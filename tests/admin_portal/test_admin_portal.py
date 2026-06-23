from __future__ import annotations

from datetime import datetime, timedelta, time
from pathlib import Path
import re
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.checkin.models.checkin_record import CheckinRecord
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission
from app.modules.identity.models.user import User
from app.modules.identity.models.user_role import UserRole
from app.modules.notification.models.notification_log import (
    NOTIFICATION_CHANNEL_MOCK,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_TYPE_RESERVATION_REMINDER,
    NotificationLog,
)
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom
from app.modules.violation.models.violation_record import (
    VIOLATION_TYPE_NO_SHOW_TIMEOUT,
    ViolationRecord,
)
from app.modules.violation.models.user_reservation_block import UserReservationBlock

HTML_HEADERS = {"accept": "text/html"}
TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates" / "admin"


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def _post_form(client: TestClient, url: str, fields: list[tuple[str, str]] | dict[str, str]):
    return client.post(
        url,
        content=urlencode(fields, doseq=True),
        headers={
            "accept": "text/html",
            "content-type": "application/x-www-form-urlencoded",
        },
    )


def _post_form_without_redirects(
    client: TestClient,
    url: str,
    fields: list[tuple[str, str]] | dict[str, str],
):
    return client.post(
        url,
        content=urlencode(fields, doseq=True),
        headers={
            "accept": "text/html",
            "content-type": "application/x-www-form-urlencoded",
        },
        follow_redirects=False,
    )


def _extract_tag(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.DOTALL)
    assert match is not None
    return match.group(0)


def _input_tag(text: str, name: str) -> str:
    return _extract_tag(text, rf'<input[^>]*name="{re.escape(name)}"[^>]*>')


def _element_tag(text: str, attribute_name: str, attribute_value: str) -> str:
    return _extract_tag(text, rf'<[^>]*{re.escape(attribute_name)}="{re.escape(attribute_value)}"[^>]*>')


def _future_slot(*, days: int = 1, start_hour: int = 10, duration_hours: int = 2) -> tuple[datetime, datetime]:
    base = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=days)
    start = base.replace(hour=start_hour)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _seed_room_with_seat(
    seed_data: dict,
    *,
    room_name: str,
    seat_code: str,
    seat_label: str,
) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name=room_name,
            location="Admin Portal Building",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code=seat_code,
            seat_label=seat_label,
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.commit()
        return {"room_id": room.id, "seat_id": seat.id}


def _get_reservation(reservation_id: int) -> Reservation:
    with SessionLocal() as session:
        reservation = session.get(Reservation, reservation_id)
        assert reservation is not None
        return reservation


def _find_created_reservation(user_id: int, seat_id: int) -> Reservation:
    with SessionLocal() as session:
        reservation = session.execute(
            select(Reservation)
            .where(Reservation.user_id == user_id, Reservation.seat_id == seat_id)
            .order_by(Reservation.id.desc())
        ).scalar_one()
        return reservation


def _seed_violation_records(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Admin Portal Violation Room",
            location="Violation Building",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        seat = Seat(
            room_id=room.id,
            seat_code="APV-01",
            seat_label="Violation Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add(seat)
        session.flush()

        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        reservation = Reservation(
            user_id=seed_data["users"]["student"],
            seat_id=seat.id,
            room_id=room.id,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status=RESERVATION_STATUS_EXPIRED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.flush()

        session.add(
            ViolationRecord(
                user_id=seed_data["users"]["student"],
                reservation_id=reservation.id,
                violation_type=VIOLATION_TYPE_NO_SHOW_TIMEOUT,
                occurred_at=now,
                remark="seeded for admin portal html page",
            )
        )
        session.commit()
        return {
            "user_id": seed_data["users"]["student"],
            "student_no": seed_data["credentials"]["student_no"],
            "room_id": room.id,
            "reservation_id": reservation.id,
        }


def _seed_admin_with_permissions(
    seed_data: dict,
    *,
    email: str,
    name: str,
    password: str,
    permission_codes: list[str],
) -> dict[str, object]:
    with SessionLocal() as session:
        permissions = session.execute(
            select(Permission).where(Permission.code.in_(permission_codes))
        ).scalars().all()
        role = Role(
            name=f"{name} Role",
            code=f"role_{email.split('@', 1)[0].replace('.', '_')}",
            description="seeded for admin portal permission-visibility test",
            is_active=True,
        )
        role.role_permissions = [RolePermission(permission=permission) for permission in permissions]

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            department_id=seed_data["departments"]["cs"],
            is_active=True,
        )
        user.user_roles = [UserRole(role=role)]
        session.add_all([role, user])
        session.commit()
        return {"user_id": user.id, "email": email, "password": password}


def _seed_numeric_conflict_user(seed_data: dict, *, student_no: str) -> int:
    with SessionLocal() as session:
        user = User(
            student_no=student_no,
            name="Numeric Conflict User",
            password_hash=hash_password("numeric-conflict-pass"),
            department_id=seed_data["departments"]["math"],
            is_active=True,
        )
        session.add(user)
        session.commit()
        return user.id


def test_required_admin_portal_pages_render_html(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    urls = [
        "/admin",
        "/admin/roles",
        "/admin/departments",
        "/admin/users/new",
        f"/admin/users/{seed_data['users']['target']}/roles",
        "/admin/rooms",
        "/admin/seats",
        "/admin/system-configs",
        "/admin/reservations/actions",
        "/admin/checkins",
        "/admin/violations",
        "/admin/notifications",
    ]

    for url in urls:
        response = client.get(url, headers=HTML_HEADERS)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")


def test_admin_login_page_renders_html(client: TestClient) -> None:
    response = client.get("/admin/login", headers=HTML_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-login"' in response.text
    assert 'data-admin-theme-source="admin_theme.css"' in response.text
    assert 'data-admin-theme-script="admin_theme.js"' in response.text
    assert "data-theme-toggle" in response.text


def test_unauthenticated_html_pages_redirect_to_login(client: TestClient) -> None:
    home_response = client.get("/admin", headers=HTML_HEADERS, follow_redirects=False)
    roles_response = client.get("/admin/roles", headers=HTML_HEADERS, follow_redirects=False)

    assert home_response.status_code == 303
    assert home_response.headers["location"] == "/admin/login?next=%2Fadmin"
    assert roles_response.status_code == 303
    assert roles_response.headers["location"] == "/admin/login?next=%2Fadmin%2Froles"


def test_admin_templates_exist_and_pages_render_from_template_files(client: TestClient, seed_data: dict) -> None:
    expected_templates = [
        "admin_theme.css",
        "admin_theme.js",
        "login.html",
        "layout.html",
        "home.html",
        "roles.html",
        "departments.html",
        "user_create.html",
        "user_roles.html",
        "rooms.html",
        "seats.html",
        "system_configs.html",
        "reservation_actions.html",
        "checkins.html",
        "violations.html",
        "notifications.html",
    ]
    for template_name in expected_templates:
        assert (TEMPLATE_ROOT / template_name).exists()

    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    home_response = client.get("/admin", headers=HTML_HEADERS)
    roles_response = client.get("/admin/roles", headers=HTML_HEADERS)

    assert 'data-layout="admin-layout"' in home_response.text
    assert 'data-template="admin-home"' in home_response.text
    assert 'data-template="admin-roles"' in roles_response.text
    assert 'data-admin-theme-source="admin_theme.css"' in home_response.text
    assert 'data-admin-theme-script="admin_theme.js"' in home_response.text
    assert "admin-theme" in home_response.text
    assert "data-theme-toggle" in home_response.text


def test_html_renderer_keeps_single_role_and_page_context_definitions() -> None:
    renderer_source = (
        Path(__file__).resolve().parents[2] / "app" / "admin_portal" / "services" / "html_renderer.py"
    ).read_text(encoding="utf-8")

    assert renderer_source.count("def _build_page_context(") == 1
    assert renderer_source.count("def _render_role_card(") == 1
    assert renderer_source.count("def _build_user_roles_context(") == 1


def test_admin_home_renders_permission_filtered_navigation(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )

    response = client.get("/admin", headers=HTML_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'href="/admin/rooms"' in response.text
    assert 'href="/admin/seats"' in response.text
    assert 'href="/admin/reservations/actions"' in response.text
    assert 'href="/admin/departments"' not in response.text
    assert 'href="/admin/users/new"' not in response.text
    assert 'href="/admin/roles"' not in response.text
    assert 'href="/admin/system-configs"' not in response.text


def test_admin_home_shows_user_create_entry_for_system_admin(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin", headers=HTML_HEADERS)

    assert response.status_code == 200
    assert 'href="/admin/users/new"' in response.text
    assert 'href="/admin/departments"' in response.text
    assert 'href="/admin/checkins"' in response.text
    assert 'href="/admin/notifications"' in response.text


def test_department_page_manages_departments_and_active_options(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    page = client.get("/admin/departments", headers=HTML_HEADERS)
    assert page.status_code == 200
    assert 'data-template="admin-departments"' in page.text
    assert 'action="/admin/departments/page"' in page.text
    assert "院系管理" in page.text

    active_create = _post_form(
        client,
        "/admin/departments/page",
        {
            "form_action": "create",
            "name": "Portal Active Department",
            "code": "PAD",
            "is_active": "on",
        },
    )
    assert active_create.status_code == 200
    assert "院系创建成功" in active_create.text

    inactive_create = _post_form(
        client,
        "/admin/departments/page",
        {
            "form_action": "create",
            "name": "Portal Inactive Department",
            "code": "PID",
        },
    )
    assert inactive_create.status_code == 200

    departments = client.get("/admin/departments").json()["items"]
    active_department = next(item for item in departments if item["code"] == "PAD")
    inactive_department = next(item for item in departments if item["code"] == "PID")

    user_create_page = client.get("/admin/users/new", headers=HTML_HEADERS)
    rooms_page = client.get("/admin/rooms", headers=HTML_HEADERS)
    assert "Portal Active Department（PAD）" in user_create_page.text
    assert "Portal Active Department（PAD）" in rooms_page.text
    assert "Portal Inactive Department（PID）" not in user_create_page.text
    assert "Portal Inactive Department（PID）" not in rooms_page.text

    deactivate_active = _post_form(
        client,
        "/admin/departments/page",
        {
            "form_action": "deactivate",
            "department_id": str(active_department["id"]),
        },
    )
    assert deactivate_active.status_code == 200
    assert "院系已停用" in deactivate_active.text

    activate_inactive = _post_form(
        client,
        "/admin/departments/page",
        {
            "form_action": "activate",
            "department_id": str(inactive_department["id"]),
        },
    )
    assert activate_inactive.status_code == 200
    assert "院系已启用" in activate_inactive.text

    user_create_page_after_toggle = client.get("/admin/users/new", headers=HTML_HEADERS)
    rooms_page_after_toggle = client.get("/admin/rooms", headers=HTML_HEADERS)
    assert "Portal Active Department（PAD）" not in user_create_page_after_toggle.text
    assert "Portal Active Department（PAD）" not in rooms_page_after_toggle.text
    assert "Portal Inactive Department（PID）" in user_create_page_after_toggle.text
    assert "Portal Inactive Department（PID）" in rooms_page_after_toggle.text

    duplicate_name = _post_form(
        client,
        "/admin/departments/page",
        {
            "form_action": "create",
            "name": "Portal Inactive Department",
            "code": "PID2",
            "is_active": "on",
        },
    )
    assert duplicate_name.status_code == 409
    assert 'data-template="admin-departments"' in duplicate_name.text
    assert "院系名称已存在" in duplicate_name.text
    assert "内部错误" not in duplicate_name.text


def test_html_pages_keep_server_side_permission_checks(client: TestClient, seed_data: dict) -> None:
    unauthenticated = client.get("/admin/roles", headers=HTML_HEADERS, follow_redirects=False)
    assert unauthenticated.status_code == 303
    assert unauthenticated.headers["location"] == "/admin/login?next=%2Fadmin%2Froles"

    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )
    forbidden = client.get("/admin/system-configs", headers=HTML_HEADERS)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"


def test_browser_login_and_logout_flow_redirects_correctly(client: TestClient, seed_data: dict) -> None:
    login_response = _post_form_without_redirects(
        client,
        "/admin/login",
        {
            "email": seed_data["credentials"]["admin_email"],
            "password": seed_data["credentials"]["admin_password"],
            "next": "/admin/rooms",
        },
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/admin/rooms"

    rooms_response = client.get("/admin/rooms", headers=HTML_HEADERS)
    assert rooms_response.status_code == 200

    logout_response = _post_form_without_redirects(client, "/admin/logout", {})
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/admin/login"

    redirected_response = client.get("/admin", headers=HTML_HEADERS, follow_redirects=False)
    assert redirected_response.status_code == 303
    assert redirected_response.headers["location"] == "/admin/login?next=%2Fadmin"


def test_browser_login_failure_returns_controlled_html(client: TestClient) -> None:
    response = _post_form_without_redirects(
        client,
        "/admin/login",
        {
            "email": "admin@example.com",
            "password": "wrong-password",
            "next": "/admin",
        },
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("text/html")
    assert "邮箱或密码错误。" in response.text


def test_roles_and_user_role_pages_submit_forms(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    roles_page = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_page.status_code == 200
    assert '/admin/roles/page' in roles_page.text
    assert '<table>' not in roles_page.text
    assert 'data-role-card="true"' in roles_page.text
    assert 'id="role-editor"' in roles_page.text
    assert 'id="user-role-entry"' in roles_page.text
    assert 'name="target_user"' in roles_page.text
    assert 'data-form-variant="admin-shared"' in roles_page.text
    assert 'data-switch-style="compact"' in roles_page.text
    assert 'data-switch-purpose="immediate-activation"' in roles_page.text
    assert "角色与分配工作台" in roles_page.text

    edit_role_page = client.get(
        f"/admin/roles?edit_role_id={seed_data['roles']['viewer']}",
        headers=HTML_HEADERS,
    )
    assert edit_role_page.status_code == 200
    assert 'id="role-editor-form"' in edit_role_page.text
    assert 'name="role_id"' in edit_role_page.text

    create_response = _post_form(
        client,
        "/admin/roles/page",
        [
            ("form_action", "create"),
            ("name", "Portal Viewer"),
            ("code", "portal_viewer"),
            ("description", "Created from the admin portal html form."),
            ("is_active", "on"),
            ("permission_ids", str(seed_data["permissions"]["admin.portal.access"])),
            ("permission_ids", str(seed_data["permissions"]["identity.roles.read"])),
        ],
    )
    assert create_response.status_code == 200
    assert create_response.headers["content-type"].startswith("text/html")

    roles_payload = client.get("/admin/roles").json()["items"]
    created_role = next(item for item in roles_payload if item["code"] == "portal_viewer")

    locate_response = _post_form_without_redirects(
        client,
        "/admin/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": seed_data["credentials"]["target_email"],
        },
    )
    assert locate_response.status_code == 303
    assert locate_response.headers["location"] == f"/admin/users/{seed_data['users']['target']}/roles"

    user_roles_page = client.get(
        f"/admin/users/{seed_data['users']['target']}/roles",
        headers=HTML_HEADERS,
    )
    assert user_roles_page.status_code == 200
    assert f'/admin/users/{seed_data["users"]["target"]}/roles/page' in user_roles_page.text
    assert "当前分配对象" in user_roles_page.text
    assert "Target User" in user_roles_page.text
    assert "更换分配对象" in user_roles_page.text
    assert "当前角色" in user_roles_page.text
    assert "调整角色" in user_roles_page.text

    assign_response = _post_form(
        client,
        f"/admin/users/{seed_data['users']['target']}/roles/page",
        [("role_ids", str(created_role["id"]))],
    )
    assert assign_response.status_code == 200
    assert assign_response.headers["content-type"].startswith("text/html")

    switch_target_response = _post_form_without_redirects(
        client,
        f"/admin/users/{seed_data['users']['target']}/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": seed_data["credentials"]["admin_email"],
        },
    )
    assert switch_target_response.status_code == 303
    assert switch_target_response.headers["location"] == f"/admin/users/{seed_data['users']['admin']}/roles"

    logout_response = client.post("/admin/auth/logout")
    assert logout_response.status_code == 200

    _login_admin(
        client,
        email=seed_data["credentials"]["target_email"],
        password=seed_data["credentials"]["target_password"],
    )
    roles_after_assignment = client.get("/admin/roles")
    assert roles_after_assignment.status_code == 200


def test_roles_page_rejects_unknown_assignment_target_with_controlled_html_error(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = _post_form(
        client,
        "/admin/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": "missing-user@example.com",
        },
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-roles"' in response.text
    assert "未找到匹配的用户，请检查用户 ID、邮箱或学号后重试。" in response.text


def test_roles_page_locates_target_by_user_id_and_student_no(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    locate_by_id_response = _post_form_without_redirects(
        client,
        "/admin/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": str(seed_data["users"]["target"]),
        },
    )
    assert locate_by_id_response.status_code == 303
    assert locate_by_id_response.headers["location"] == f"/admin/users/{seed_data['users']['target']}/roles"

    locate_by_student_no_response = _post_form_without_redirects(
        client,
        "/admin/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": seed_data["credentials"]["student_no"],
        },
    )
    assert locate_by_student_no_response.status_code == 303
    assert locate_by_student_no_response.headers["location"] == f"/admin/users/{seed_data['users']['student']}/roles"


def test_user_roles_page_shows_student_number_separately_from_notification_email(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    create_student = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Role Page Student",
            "student_no": "20248889",
            "notification_email": "role.student@example.com",
            "password": "role-page-student-pass",
            "department_id": seed_data["departments"]["cs"],
        },
    )
    assert create_student.status_code == 200
    created_student_id = create_student.json()["data"]["id"]

    response = client.get(
        f"/admin/users/{created_student_id}/roles",
        headers=HTML_HEADERS,
    )

    assert response.status_code == 200
    assert "<dt>学号</dt><dd>20248889</dd>" in response.text
    assert "<dt>通知邮箱</dt><dd>role.student@example.com</dd>" in response.text
    assert "<dt>邮箱</dt><dd>role.student@example.com</dd>" not in response.text
    assert 'name="target_user"' in response.text
    assert 'value="20248889"' in _input_tag(response.text, "target_user")


def test_roles_page_rejects_ambiguous_numeric_assignment_target_with_controlled_html_error(
    client: TestClient,
    seed_data: dict,
) -> None:
    _seed_numeric_conflict_user(seed_data, student_no=str(seed_data["users"]["target"]))
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = _post_form(
        client,
        "/admin/roles/page",
        {
            "form_action": "locate_user_roles",
            "target_user": str(seed_data["users"]["target"]),
        },
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-roles"' in response.text
    assert "该数字同时匹配到了用户 ID 和学号，请改用邮箱，或使用 id:/student: 前缀重新输入。" in response.text


def test_home_hides_permissions_entry_when_only_permissions_read_is_granted(
    client: TestClient,
    seed_data: dict,
) -> None:
    permissions_reader = _seed_admin_with_permissions(
        seed_data,
        email="permissions-only@example.com",
        name="Permissions Only",
        password="permissions-only-pass",
        permission_codes=["admin.portal.access", "identity.permissions.read"],
    )

    _login_admin(
        client,
        email=str(permissions_reader["email"]),
        password=str(permissions_reader["password"]),
    )

    home_response = client.get("/admin", headers=HTML_HEADERS)
    assert home_response.status_code == 200
    assert 'href="/admin/roles#permission-reference"' not in home_response.text

    roles_response = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_response.status_code == 403
    assert roles_response.json()["code"] == "forbidden"


def test_home_hides_user_role_entry_when_only_user_role_write_is_granted(
    client: TestClient,
    seed_data: dict,
) -> None:
    user_roles_writer = _seed_admin_with_permissions(
        seed_data,
        email="user-roles-only@example.com",
        name="User Roles Only",
        password="user-roles-only-pass",
        permission_codes=["admin.portal.access", "identity.users.roles.write"],
    )

    _login_admin(
        client,
        email=str(user_roles_writer["email"]),
        password=str(user_roles_writer["password"]),
    )

    home_response = client.get("/admin", headers=HTML_HEADERS)
    assert home_response.status_code == 200
    assert 'href="/admin/roles#user-role-entry"' not in home_response.text

    user_roles_page = client.get(
        f"/admin/users/{seed_data['users']['target']}/roles",
        headers=HTML_HEADERS,
    )
    assert user_roles_page.status_code == 200

    roles_response = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_response.status_code == 403
    assert roles_response.json()["code"] == "forbidden"


def test_user_create_page_is_visible_when_users_write_is_granted(
    client: TestClient,
    seed_data: dict,
) -> None:
    user_creator = _seed_admin_with_permissions(
        seed_data,
        email="user-creator@example.com",
        name="User Creator",
        password="user-creator-pass",
        permission_codes=["admin.portal.access", "identity.users.write"],
    )

    _login_admin(
        client,
        email=str(user_creator["email"]),
        password=str(user_creator["password"]),
    )

    home_response = client.get("/admin", headers=HTML_HEADERS)
    assert home_response.status_code == 200
    assert 'href="/admin/users/new"' in home_response.text
    assert 'href="/admin/roles"' not in home_response.text

    create_page = client.get("/admin/users/new", headers=HTML_HEADERS)
    assert create_page.status_code == 200
    assert 'data-template="admin-user-create"' in create_page.text

    roles_response = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_response.status_code == 403
    assert roles_response.json()["code"] == "forbidden"


def test_user_create_page_submits_student_and_admin_forms(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    user_create_page = client.get("/admin/users/new", headers=HTML_HEADERS)
    assert user_create_page.status_code == 200
    assert 'data-template="admin-user-create"' in user_create_page.text
    assert 'action="/admin/users/new/page"' in user_create_page.text
    assert 'name="account_type"' in user_create_page.text
    assert 'name="student_no"' in user_create_page.text
    assert 'name="notification_email"' in user_create_page.text
    assert "通知邮箱" in user_create_page.text
    assert 'name="email"' in user_create_page.text
    assert 'name="password"' in user_create_page.text
    assert 'name="department_id"' in user_create_page.text
    assert 'data-switch-style="compact"' in user_create_page.text
    assert 'data-switch-purpose="immediate-activation"' in user_create_page.text
    assert 'data-account-type-form="user-create"' in user_create_page.text
    assert 'data-account-type-script="user-create"' in user_create_page.text

    student_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "student",
            "name": "Portal Student",
            "student_no": "20248888",
            "notification_email": "portal.student@example.com",
            "password": "portal-student-pass",
            "department_id": str(seed_data["departments"]["cs"]),
            "is_active": "on",
        },
    )
    assert student_response.status_code == 200
    assert "学生账号已创建" in student_response.text
    assert 'data-created-user-summary="true"' in student_response.text
    assert "portal.student@example.com" in student_response.text
    assert "portal-student-pass" not in student_response.text
    assert "password_hash" not in student_response.text

    with SessionLocal() as session:
        created_student = session.scalar(select(User).where(User.student_no == "20248888"))
        assert created_student is not None
        assert created_student.email == "portal.student@example.com"

    admin_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "admin",
            "name": "Portal Admin",
            "email": "portal-admin",
            "password": "portal-admin-pass",
            "department_id": str(seed_data["departments"]["math"]),
        },
    )
    assert admin_response.status_code == 200
    assert "管理员账号已创建" in admin_response.text
    assert "继续分配管理员角色" in admin_response.text
    assert "portal-admin-pass" not in admin_response.text
    assert "password_hash" not in admin_response.text
    assert "通知邮箱" not in admin_response.text.split('data-created-user-summary="true"', 1)[1].split("</dl>", 1)[0]

    with SessionLocal() as session:
        created_admin = session.scalar(select(User).where(User.email == "portal-admin"))
        assert created_admin is not None
        assert created_admin.student_no is None

    assert f'/admin/users/{created_admin.id}/roles' in admin_response.text


def test_user_create_page_defaults_to_student_identifier_state(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/users/new", headers=HTML_HEADERS)

    assert response.status_code == 200
    form_tag = _element_tag(response.text, "data-account-type-form", "user-create")
    student_group_tag = _element_tag(response.text, "data-identifier-group", "student")
    admin_group_tag = _element_tag(response.text, "data-identifier-group", "admin")
    notification_group_tag = _element_tag(response.text, "data-notification-group", "student")
    student_input_tag = _input_tag(response.text, "student_no")
    admin_input_tag = _input_tag(response.text, "email")
    notification_input_tag = _input_tag(response.text, "notification_email")

    assert 'data-current-account-type="student"' in form_tag
    assert 'data-group-state="active"' in student_group_tag
    assert "hidden" not in student_group_tag
    assert 'data-group-state="active"' in notification_group_tag
    assert "hidden" not in notification_group_tag
    assert 'data-group-state="inactive"' in admin_group_tag
    assert "hidden" in admin_group_tag
    assert "required" in student_input_tag
    assert "disabled" not in student_input_tag
    assert "required" not in notification_input_tag
    assert "disabled" not in notification_input_tag
    assert "disabled" in admin_input_tag
    assert "required" not in admin_input_tag
    assert "data-account-type-current-hint" in response.text


def test_user_create_page_returns_controlled_html_errors(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    invalid_department_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "student",
            "name": "Invalid Department User",
            "student_no": "20249998",
            "notification_email": "invalid.department.student@example.com",
            "password": "invalid-department-pass",
            "department_id": "999999",
            "is_active": "on",
        },
    )
    assert invalid_department_response.status_code == 400
    assert 'data-template="admin-user-create"' in invalid_department_response.text
    assert "院系" in invalid_department_response.text
    assert "内部错误" not in invalid_department_response.text
    assert 'data-current-account-type="student"' in _element_tag(
        invalid_department_response.text,
        "data-account-type-form",
        "user-create",
    )
    assert 'data-group-state="active"' in _element_tag(
        invalid_department_response.text,
        "data-identifier-group",
        "student",
    )
    assert "hidden" in _element_tag(
        invalid_department_response.text,
        "data-identifier-group",
        "admin",
    )
    assert "required" in _input_tag(invalid_department_response.text, "student_no")
    assert "invalid.department.student@example.com" in _input_tag(
        invalid_department_response.text,
        "notification_email",
    )
    assert "disabled" not in _input_tag(invalid_department_response.text, "notification_email")
    assert "disabled" in _input_tag(invalid_department_response.text, "email")

    duplicate_identifier_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "admin",
            "name": "Duplicate Admin",
            "email": seed_data["credentials"]["admin_email"],
            "password": "duplicate-pass",
        },
    )
    assert duplicate_identifier_response.status_code == 409
    assert 'data-template="admin-user-create"' in duplicate_identifier_response.text
    assert "登录标识" in duplicate_identifier_response.text
    assert 'data-current-account-type="admin"' in _element_tag(
        duplicate_identifier_response.text,
        "data-account-type-form",
        "user-create",
    )
    assert 'data-group-state="active"' in _element_tag(
        duplicate_identifier_response.text,
        "data-identifier-group",
        "admin",
    )
    assert "hidden" in _element_tag(
        duplicate_identifier_response.text,
        "data-identifier-group",
        "student",
    )
    assert "required" in _input_tag(duplicate_identifier_response.text, "email")
    assert "disabled" in _input_tag(duplicate_identifier_response.text, "student_no")
    assert "disabled" in _input_tag(duplicate_identifier_response.text, "notification_email")


def test_user_create_page_returns_identifier_validation_html_errors(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    missing_identifier_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "student",
            "name": "Missing Identifier User",
            "password": "missing-html-pass",
        },
    )
    assert missing_identifier_response.status_code == 400
    assert 'data-template="admin-user-create"' in missing_identifier_response.text
    assert "missing-html-pass" not in missing_identifier_response.text
    assert "Value error" in missing_identifier_response.text

    multiple_identifier_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "admin",
            "name": "Multiple Identifier User",
            "student_no": "20249996",
            "email": "multiple-html-admin",
            "password": "multiple-html-pass",
        },
    )
    assert multiple_identifier_response.status_code == 400
    assert 'data-template="admin-user-create"' in multiple_identifier_response.text
    assert "multiple-html-pass" not in multiple_identifier_response.text
    assert "Value error" in multiple_identifier_response.text


def test_user_create_page_requires_users_write_permission(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )

    get_response = client.get("/admin/users/new", headers=HTML_HEADERS)
    assert get_response.status_code == 403
    assert get_response.json()["code"] == "forbidden"

    post_response = _post_form(
        client,
        "/admin/users/new/page",
        {
            "account_type": "student",
            "name": "Blocked Portal User",
            "student_no": "20249997",
            "password": "blocked-pass",
        },
    )
    assert post_response.status_code == 403
    assert post_response.json()["code"] == "forbidden"


def test_room_and_seat_pages_submit_forms(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    rooms_page = client.get("/admin/rooms", headers=HTML_HEADERS)
    assert rooms_page.status_code == 200
    assert "新建自习室" in rooms_page.text
    assert "所属院系" in rooms_page.text
    assert 'name="access_scope"' in rooms_page.text
    assert 'name="department_id"' in rooms_page.text
    assert 'Department ID' not in rooms_page.text
    assert '<input name="department_id"' not in rooms_page.text
    assert 'data-form-variant="admin-shared"' in rooms_page.text
    assert 'data-switch-style="compact"' in rooms_page.text
    assert 'data-switch-purpose="immediate-activation"' in rooms_page.text
    rooms_template = (TEMPLATE_ROOT / "rooms.html").read_text(encoding="utf-8")
    assert "function bindRoomForm(form)" in rooms_template
    assert "bindRoomForm(forms[index])" in rooms_template

    create_room_response = _post_form(
        client,
        "/admin/rooms/page",
        {
            "form_action": "create",
            "name": "Admin Portal Room",
            "location": "Library Annex",
            "access_scope": "department",
            "department_id": str(seed_data["departments"]["cs"]),
            "is_active": "on",
            "open_time": "08:00",
            "close_time": "21:00",
        },
    )
    assert create_room_response.status_code == 200

    rooms_payload = client.get("/admin/rooms").json()["items"]
    room = next(item for item in rooms_payload if item["name"] == "Admin Portal Room")

    update_room_response = _post_form(
        client,
        "/admin/rooms/page",
        {
            "form_action": "update",
            "room_id": str(room["id"]),
            "name": "Admin Portal Room Updated",
            "location": "Library Annex East",
            "access_scope": "public",
            "department_id": "",
            "is_active": "on",
            "open_time": "09:00",
            "close_time": "22:00",
        },
    )
    assert update_room_response.status_code == 200

    updated_rooms = client.get("/admin/rooms").json()["items"]
    updated_room = next(item for item in updated_rooms if item["id"] == room["id"])
    assert updated_room["name"] == "Admin Portal Room Updated"
    assert updated_room["department_id"] is None

    seats_page = client.get("/admin/seats", params={"room_id": room["id"]}, headers=HTML_HEADERS)
    assert seats_page.status_code == 200
    assert 'data-form-variant="admin-shared"' in seats_page.text
    assert 'data-switch-style="compact"' in seats_page.text
    assert 'data-switch-purpose="immediate-activation"' in seats_page.text
    assert 'data-toggle-group="seat-attributes"' in seats_page.text
    assert 'class="toggle-card"' in seats_page.text
    assert "筛选与新建座位" in seats_page.text
    assert "移动导轨插座" in seats_page.text

    create_seat_response = _post_form(
        client,
        "/admin/seats/page",
        {
            "form_action": "create",
            "filter_room_id": str(room["id"]),
            "room_id": str(room["id"]),
            "seat_code": "APR-01",
            "seat_label": "Admin Portal Seat",
            "is_active": "on",
            "has_power_socket": "on",
        },
    )
    assert create_seat_response.status_code == 200

    seats_payload = client.get("/admin/seats", params={"room_id": room["id"]}).json()["items"]
    seat = next(item for item in seats_payload if item["seat_code"] == "APR-01")

    update_seat_response = _post_form(
        client,
        "/admin/seats/page",
        {
            "form_action": "update",
            "seat_id": str(seat["id"]),
            "filter_room_id": str(room["id"]),
            "room_id": str(room["id"]),
            "seat_code": "APR-02",
            "seat_label": "Admin Portal Seat Updated",
            "is_active": "on",
            "has_power_socket": "on",
            "has_track_socket": "on",
        },
    )
    assert update_seat_response.status_code == 200

    updated_seats = client.get("/admin/seats", params={"room_id": room["id"]}).json()["items"]
    updated_seat = next(item for item in updated_seats if item["id"] == seat["id"])
    assert updated_seat["seat_code"] == "APR-02"
    assert updated_seat["has_track_socket"] is True


def test_rooms_page_rejects_invalid_department_selection_with_controlled_html_error(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = _post_form(
        client,
        "/admin/rooms/page",
        {
            "form_action": "create",
            "name": "Invalid Department Room",
            "location": "Teaching Building",
            "access_scope": "department",
            "department_id": "999999",
            "is_active": "on",
            "open_time": "08:00",
            "close_time": "20:00",
        },
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-rooms"' in response.text
    assert "所选院系不存在或已停用，请重新选择。" in response.text
    assert "内部错误" not in response.text


def test_system_config_and_reservation_action_pages_submit_forms(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    system_configs_page = client.get("/admin/system-configs", headers=HTML_HEADERS)
    assert system_configs_page.status_code == 200

    update_config_response = _post_form(
        client,
        "/admin/system-configs/page",
        {
            "config_key": "max_reservation_hours",
            "config_value": "6",
        },
    )
    assert update_config_response.status_code == 200

    configs = client.get("/admin/system-configs").json()["items"]
    config_values = {item["config_key"]: item["config_value"] for item in configs}
    assert config_values["max_reservation_hours"] == 6

    reservation_page = client.get("/admin/reservations/actions", headers=HTML_HEADERS)
    assert reservation_page.status_code == 200

    seeded = _seed_room_with_seat(
        seed_data,
        room_name="Admin Portal Reservation Room",
        seat_code="APR-CREATE-01",
        seat_label="Reservation Seat",
    )
    start_time, end_time = _future_slot(start_hour=10, duration_hours=2)

    create_reservation_response = _post_form(
        client,
        "/admin/reservations/actions/page",
        {
            "form_action": "create",
            "user_id": str(seed_data["users"]["student"]),
            "seat_id": str(seeded["seat_id"]),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert create_reservation_response.status_code == 200

    reservation = _find_created_reservation(seed_data["users"]["student"], seeded["seat_id"])
    assert reservation.status == RESERVATION_STATUS_BOOKED

    cancel_reservation_response = _post_form(
        client,
        "/admin/reservations/actions/page",
        {
            "form_action": "cancel",
            "reservation_id": str(reservation.id),
            "reason": "Cancelled from admin portal html form",
        },
    )
    assert cancel_reservation_response.status_code == 200

    cancelled_reservation = _get_reservation(reservation.id)
    assert cancelled_reservation.status == RESERVATION_STATUS_CANCELLED
    assert cancelled_reservation.cancel_reason == "Cancelled from admin portal html form"


def test_checkins_page_shows_dynamic_code_and_lists_records(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    seeded = _seed_room_with_seat(
        seed_data,
        room_name="Admin Portal Checkin Room",
        seat_code="APC-01",
        seat_label="Checkin Seat",
    )
    today = datetime.now().date()
    reservation_id = _insert_admin_portal_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=seeded["seat_id"],
        room_id=seeded["room_id"],
        start_time=datetime.combine(today, time(9, 0)),
        end_time=datetime.combine(today, time(10, 0)),
    )
    with SessionLocal() as session:
        session.add(
            CheckinRecord(
                reservation_id=reservation_id,
                user_id=seed_data["users"]["student"],
                room_id=seeded["room_id"],
                seat_id=seeded["seat_id"],
                checkin_method="CODE",
                checkin_at=datetime.combine(today, time(9, 5)),
                is_valid=True,
            ),
        )
        session.commit()

    page = client.get("/admin/checkins", params={"room_id": seeded["room_id"]}, headers=HTML_HEADERS)
    assert page.status_code == 200
    assert 'data-template="admin-checkins"' in page.text
    assert "动态签到码" in page.text
    assert "当前动态签到码" in page.text
    assert 'action="/admin/checkins/page"' not in page.text
    assert "生成或查看签到码" not in page.text
    assert str(reservation_id) in page.text

    payload_response = client.get("/admin/checkins", params={"room_id": seeded["room_id"]})
    assert payload_response.status_code == 200
    payload = payload_response.json()
    assert payload["code"]["room_id"] == seeded["room_id"]
    assert payload["code"]["code"]
    assert payload["code"]["time_slice_start"]
    assert payload["code"]["expires_at"]
    assert payload["items"]


def test_checkins_page_returns_html_for_invalid_room_id(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    page = client.get("/admin/checkins", params={"room_id": "999999"}, headers=HTML_HEADERS)
    assert page.status_code == 404
    assert page.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-checkins"' in page.text
    assert not page.text.lstrip().startswith("{")


def test_checkins_page_returns_json_for_invalid_room_id_when_not_html(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    page = client.get("/admin/checkins", params={"room_id": "999999"})
    assert page.status_code == 404
    assert page.headers["content-type"].startswith("application/json")
    payload = page.json()
    assert payload["code"] == "not_found"
    assert payload["details"]


def test_notifications_page_lists_logs_without_manual_task_controls(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    seeded = _seed_room_with_seat(
        seed_data,
        room_name="Admin Portal Notification Room",
        seat_code="APN-01",
        seat_label="Notification Seat",
    )
    now = (datetime.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    reservation_id = _insert_admin_portal_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=seeded["seat_id"],
        room_id=seeded["room_id"],
        start_time=now + timedelta(minutes=15),
        end_time=now + timedelta(hours=1),
    )
    with SessionLocal() as session:
        session.add(
            NotificationLog(
                user_id=seed_data["users"]["student"],
                reservation_id=reservation_id,
                notification_type=NOTIFICATION_TYPE_RESERVATION_REMINDER,
                channel=NOTIFICATION_CHANNEL_MOCK,
                status=NOTIFICATION_STATUS_SENT,
                message="seeded notification log",
                sent_at=now - timedelta(minutes=1),
            ),
        )
        session.commit()

    page = client.get("/admin/notifications", params={"reservation_id": reservation_id}, headers=HTML_HEADERS)
    assert page.status_code == 200
    assert 'data-template="admin-notifications"' in page.text
    assert str(reservation_id) in page.text
    assert NOTIFICATION_TYPE_RESERVATION_REMINDER in page.text
    assert "通道状态" in page.text
    assert "后台调度器" in page.text
    assert "超时未签到释放通知" in page.text
    manual_task_label = "手动" + "触发任务"
    execute_task_label = "执行" + "任务"
    confusing_cancel_copy = "自动" + "取消"
    removed_path = "/admin/notifications" + "/page"
    assert manual_task_label not in page.text
    assert execute_task_label not in page.text
    assert confusing_cancel_copy not in page.text
    assert f'action="{removed_path}"' not in page.text

    removed_entry = _post_form(
        client,
        removed_path,
        {
            "notification_type": "NO_SHOW_REMINDER",
            "now": now.isoformat(timespec="minutes"),
        },
    )
    assert removed_entry.status_code == 404


def test_notifications_page_returns_json_bad_request_for_invalid_numeric_filter(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/notifications", params={"reservation_id": "abc"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["code"] == "bad_request"
    assert "预约 ID 必须是数字。" in payload["message"]
    assert 'data-template="admin-notifications"' not in response.text


def test_violations_page_renders_filtered_html_results(client: TestClient, seed_data: dict) -> None:
    seeded = _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/violations",
        params={"student_no": seeded["student_no"]},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert VIOLATION_TYPE_NO_SHOW_TIMEOUT in response.text
    assert str(seeded["user_id"]) in response.text
    assert seeded["student_no"] in response.text
    assert str(seeded["room_id"]) in response.text

    all_response = client.get("/admin/violations", headers=HTML_HEADERS)
    assert all_response.status_code == 200
    assert str(seeded["reservation_id"]) in all_response.text


def test_violations_page_shows_user_summary_and_manual_block_forms(
    client: TestClient,
    seed_data: dict,
) -> None:
    seeded = _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    page = client.get(
        "/admin/violations",
        params={"user_id": seeded["user_id"]},
        headers=HTML_HEADERS,
    )

    assert page.status_code == 200
    assert "用户统计与限制状态" in page.text
    assert "违约次数" in page.text
    assert "未限制" in page.text
    assert "开启手动限制" in page.text

    activate = _post_form(
        client,
        f"/admin/violations/users/{seeded['user_id']}/manual-block",
        {"reason": "Manual block from admin portal"},
    )

    assert activate.status_code == 200
    assert "手动预约限制已开启" in activate.text
    assert "限制中" in activate.text
    assert "Manual block from admin portal" in activate.text
    assert "解除手动限制" in activate.text

    with SessionLocal() as session:
        block = session.scalar(
            select(UserReservationBlock).where(UserReservationBlock.user_id == seeded["user_id"])
        )
        assert block is not None
        block_id = block.id

    release = _post_form(
        client,
        f"/admin/violations/users/{seeded['user_id']}/manual-block/release",
        {},
    )

    assert release.status_code == 200
    assert "手动预约限制已解除" in release.text
    assert "开启手动限制" in release.text
    with SessionLocal() as session:
        persisted = session.get(UserReservationBlock, block_id)
        assert persisted is not None
        assert persisted.released_at is not None


def test_violations_page_hides_manual_block_forms_without_write_permission(
    client: TestClient,
    seed_data: dict,
) -> None:
    seeded = _seed_violation_records(seed_data)
    with SessionLocal() as session:
        session.add(UserRole(user_id=seed_data["users"]["target"], role_id=seed_data["roles"]["viewer"]))
        session.commit()
    _login_admin(
        client,
        email=seed_data["credentials"]["target_email"],
        password=seed_data["credentials"]["target_password"],
    )

    page = client.get(
        "/admin/violations",
        params={"user_id": seeded["user_id"]},
        headers=HTML_HEADERS,
    )

    assert page.status_code == 200
    assert "用户统计与限制状态" in page.text
    assert "开启手动限制" not in page.text
    assert "解除手动限制" not in page.text

    forbidden = _post_form(
        client,
        f"/admin/violations/users/{seeded['user_id']}/manual-block",
        {"reason": "Should fail"},
    )
    assert forbidden.status_code == 403


def test_violations_page_returns_html_bad_request_for_invalid_date_range(client: TestClient, seed_data: dict) -> None:
    _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/violations",
        params={"date_from": "2026-04-18", "date_to": "2026-04-17"},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-violations"' in response.text
    assert "开始日期不能晚于结束日期。" in response.text
    assert "bad_request" not in response.text


def test_violations_page_returns_html_bad_request_for_invalid_numeric_filter(
    client: TestClient,
    seed_data: dict,
) -> None:
    _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/violations",
        params={"user_id": "abc"},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-violations"' in response.text
    assert "用户 ID 必须是数字。" in response.text
    assert "bad_request" not in response.text


def test_violations_page_returns_json_bad_request_for_invalid_date_range(client: TestClient, seed_data: dict) -> None:
    _seed_violation_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/violations",
        params={"date_from": "2026-04-18", "date_to": "2026-04-17"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "bad_request"
    assert "开始日期不能晚于结束日期。" in payload["message"]
    assert payload["details"]


def _insert_admin_portal_reservation(
    *,
    user_id: int,
    seat_id: int,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    status: str = RESERVATION_STATUS_BOOKED,
) -> int:
    with SessionLocal() as session:
        reservation = Reservation(
            user_id=user_id,
            seat_id=seat_id,
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            status=status,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add(reservation)
        session.commit()
        return reservation.id


def test_admin_home_shows_reservation_records_and_statistics_entries(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin", headers=HTML_HEADERS)

    assert response.status_code == 200
    assert 'href="/admin/reservations/records"' in response.text
    assert 'href="/admin/statistics"' in response.text


def test_reservation_records_page_renders_filtered_html_results(client: TestClient, seed_data: dict) -> None:
    seeded = _seed_room_with_seat(
        seed_data,
        room_name="Admin Portal Record Room",
        seat_code="APR-RECORD-01",
        seat_label="Record Seat",
    )
    start_time, end_time = _future_slot(days=2, start_hour=9, duration_hours=2)
    reservation_id = _insert_admin_portal_reservation(
        user_id=seed_data["users"]["student"],
        seat_id=seeded["seat_id"],
        room_id=seeded["room_id"],
        start_time=start_time,
        end_time=end_time,
    )
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/reservations/records",
        params={"user_id": seed_data["users"]["student"]},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-reservation-records"' in response.text
    assert str(reservation_id) in response.text
    assert str(seed_data["users"]["student"]) in response.text


def test_reservation_records_page_returns_html_bad_request_for_invalid_status(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/reservations/records",
        params={"status": "INVALID"},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-reservation-records"' in response.text
    assert "内部错误" not in response.text


def test_reservation_records_page_returns_html_bad_request_for_invalid_date_range(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get(
        "/admin/reservations/records",
        params={"date_from": "2026-04-20", "date_to": "2026-04-19"},
        headers=HTML_HEADERS,
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-reservation-records"' in response.text
    assert "date_from" in response.text


def test_statistics_page_renders_html_results(client: TestClient, seed_data: dict) -> None:
    from tests.violation.test_admin_statistics import _seed_statistics_records

    params = _seed_statistics_records(seed_data)
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/statistics", params=params, headers=HTML_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-template="admin-statistics"' in response.text
    assert "Usage Alpha Room" in response.text
    assert "Usage Beta Room" in response.text


def test_roles_page_can_deactivate_role(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_response = client.post(
        "/admin/roles",
        json={
            "name": "Portal Deactivate Role",
            "code": "portal_deactivate_role",
            "description": "Created for admin portal deactivate flow.",
            "is_active": True,
            "permission_ids": [seed_data["permissions"]["admin.portal.access"]],
        },
    )
    assert create_response.status_code == 200
    role_id = create_response.json()["data"]["id"]

    roles_page = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_page.status_code == 200
    assert 'value="deactivate"' in roles_page.text

    deactivate_response = _post_form(
        client,
        "/admin/roles/page",
        {
            "form_action": "deactivate",
            "role_id": str(role_id),
        },
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.headers["content-type"].startswith("text/html")

    roles_payload = client.get("/admin/roles").json()["items"]
    deactivated_role = next(item for item in roles_payload if item["id"] == role_id)
    assert deactivated_role["is_active"] is False


def test_roles_page_can_delete_unassigned_role(client: TestClient, seed_data: dict) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_response = client.post(
        "/admin/roles",
        json={
            "name": "Portal Delete Role",
            "code": "portal_delete_role",
            "description": "Created for admin portal delete flow.",
            "is_active": True,
            "permission_ids": [seed_data["permissions"]["admin.portal.access"]],
        },
    )
    assert create_response.status_code == 200
    role_id = create_response.json()["data"]["id"]

    roles_page = client.get("/admin/roles", headers=HTML_HEADERS)
    assert roles_page.status_code == 200
    assert 'value="delete"' in roles_page.text
    assert "删除角色" in roles_page.text

    delete_response = _post_form(
        client,
        "/admin/roles/page",
        {
            "form_action": "delete",
            "role_id": str(role_id),
        },
    )

    assert delete_response.status_code == 200
    assert delete_response.headers["content-type"].startswith("text/html")
    assert "角色已删除" in delete_response.text

    roles_payload = client.get("/admin/roles").json()["items"]
    assert all(item["id"] != role_id for item in roles_payload)
