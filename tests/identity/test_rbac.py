from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.errors import AuthorizationError
from app.core.security import verify_password
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.models.user import User
from app.modules.identity.services.permission_service import PermissionService


def _login_admin(client: TestClient, email: str, password: str):
    return client.post("/admin/auth/login", json={"email": email, "password": password})


def test_unauthenticated_admin_endpoint_fails(client: TestClient) -> None:
    response = client.get("/admin/roles")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_list_roles_requires_read_permission(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["limited_admin_email"],
        seed_data["credentials"]["limited_admin_password"],
    )
    assert login_response.status_code == 200

    response = client.get("/admin/roles")

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_create_role_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/roles",
        json={
            "name": "Resource Manager",
            "code": "resource_manager",
            "description": "Manages room resources.",
            "is_active": True,
            "permission_ids": [
                seed_data["permissions"]["admin.portal.access"],
                seed_data["permissions"]["identity.roles.read"],
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["code"] == "resource_manager"
    assert {item["code"] for item in payload["data"]["permissions"]} == {
        "admin.portal.access",
        "identity.roles.read",
    }


def test_update_role_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.put(
        f"/admin/roles/{seed_data['roles']['viewer']}",
        json={
            "name": "Viewer",
            "code": "viewer",
            "description": "Updated viewer role.",
            "is_active": True,
            "permission_ids": [seed_data["permissions"]["admin.portal.access"]],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["description"] == "Updated viewer role."
    assert [item["code"] for item in payload["data"]["permissions"]] == ["admin.portal.access"]


def test_list_permissions_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.get("/admin/permissions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 6
    assert any(item["code"] == "identity.users.roles.write" for item in payload["items"])


def test_create_student_user_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Fresh Student",
            "student_no": "20245555",
            "notification_email": "fresh.student@example.com",
            "password": "fresh-student-pass",
            "department_id": seed_data["departments"]["cs"],
            "is_active": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["account_type"] == "student"
    assert payload["data"]["student_no"] == "20245555"
    assert payload["data"]["email"] is None
    assert payload["data"]["notification_email"] == "fresh.student@example.com"
    assert "password" not in payload["data"]
    assert "password_hash" not in payload["data"]

    with SessionLocal() as session:
        created_user = session.scalar(select(User).where(User.student_no == "20245555"))
        assert created_user is not None
        assert created_user.email == "fresh.student@example.com"
        assert created_user.password_hash != "fresh-student-pass"
        assert verify_password("fresh-student-pass", created_user.password_hash)

    student_login = client.post(
        "/student/auth/login",
        json={"student_no": "20245555", "password": "fresh-student-pass"},
    )
    assert student_login.status_code == 200

    email_student_login = client.post(
        "/student/auth/login",
        json={"student_no": "fresh.student@example.com", "password": "fresh-student-pass"},
    )
    assert email_student_login.status_code == 401

    admin_login_with_student_notification_email = client.post(
        "/admin/auth/login",
        json={"email": "fresh.student@example.com", "password": "fresh-student-pass"},
    )
    assert admin_login_with_student_notification_email.status_code == 401


def test_create_admin_user_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/users",
        json={
            "account_type": "admin",
            "name": "Ops Admin",
            "email": "ops-admin",
            "password": "ops-admin-pass",
            "department_id": seed_data["departments"]["math"],
            "is_active": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["account_type"] == "admin"
    assert payload["data"]["email"] == "ops-admin"
    assert payload["data"]["notification_email"] is None
    assert payload["data"]["student_no"] is None
    assert payload["data"]["is_active"] is False
    assert "password" not in payload["data"]
    assert "password_hash" not in payload["data"]

    with SessionLocal() as session:
        created_user = session.scalar(select(User).where(User.email == "ops-admin"))
        assert created_user is not None
        assert created_user.password_hash != "ops-admin-pass"
        assert verify_password("ops-admin-pass", created_user.password_hash)


def test_create_user_rejects_duplicate_identifier(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    duplicate_student = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Duplicate Student",
            "student_no": seed_data["credentials"]["student_no"],
            "password": "duplicate-pass",
        },
    )
    assert duplicate_student.status_code == 409
    assert duplicate_student.json()["code"] == "conflict"

    duplicate_admin = client.post(
        "/admin/users",
        json={
            "account_type": "admin",
            "name": "Duplicate Admin",
            "email": seed_data["credentials"]["admin_email"],
            "password": "duplicate-pass",
        },
    )
    assert duplicate_admin.status_code == 409
    assert duplicate_admin.json()["code"] == "conflict"

    duplicate_notification_email = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Duplicate Notification Email",
            "student_no": "20245556",
            "notification_email": seed_data["credentials"]["admin_email"],
            "password": "duplicate-pass",
        },
    )
    assert duplicate_notification_email.status_code == 409
    duplicate_notification_payload = duplicate_notification_email.json()
    assert duplicate_notification_payload["code"] == "conflict"
    assert duplicate_notification_payload["details"]["field"] == "notification_email"


def test_create_student_user_rejects_invalid_notification_email(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Invalid Email Student",
            "student_no": "20245557",
            "notification_email": "invalid-email",
            "password": "invalid-email-pass",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert "invalid-email-pass" not in response.text


def test_create_user_rejects_invalid_department(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Invalid Department",
            "student_no": "20246666",
            "password": "invalid-department-pass",
            "department_id": 999999,
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "bad_request"
    assert "院系" in payload["message"]


def test_create_user_rejects_missing_or_multiple_identifiers(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    missing_identifier = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Missing Identifier",
            "password": "missing-identifier-pass",
        },
    )
    assert missing_identifier.status_code == 422
    missing_payload = missing_identifier.json()
    assert missing_payload["code"] == "validation_error"
    assert "missing-identifier-pass" not in missing_identifier.text
    assert all(set(item.keys()) == {"loc", "type", "msg"} for item in missing_payload["details"])

    multiple_identifiers = client.post(
        "/admin/users",
        json={
            "account_type": "admin",
            "name": "Multiple Identifiers",
            "student_no": "20248881",
            "email": "multi-id-admin",
            "password": "multiple-identifiers-pass",
        },
    )
    assert multiple_identifiers.status_code == 422
    multiple_payload = multiple_identifiers.json()
    assert multiple_payload["code"] == "validation_error"
    assert "multiple-identifiers-pass" not in multiple_identifiers.text
    assert all(set(item.keys()) == {"loc", "type", "msg"} for item in multiple_payload["details"])


def test_create_user_requires_users_write_permission(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["limited_admin_email"],
        seed_data["credentials"]["limited_admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/users",
        json={
            "account_type": "student",
            "name": "Blocked User",
            "student_no": "20247777",
            "password": "blocked-user-pass",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_write_endpoint_requires_write_permission(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["limited_admin_email"],
        seed_data["credentials"]["limited_admin_password"],
    )
    assert login_response.status_code == 200

    response = client.post(
        "/admin/roles",
        json={
            "name": "Blocked Role",
            "code": "blocked_role",
            "description": "Should not be created.",
            "is_active": True,
            "permission_ids": [],
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_assign_roles_success_and_new_admin_can_login(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    assign_response = client.post(
        f"/admin/users/{seed_data['users']['target']}/roles",
        json={"role_ids": [seed_data["roles"]["viewer"]]},
    )

    assert assign_response.status_code == 200
    assert assign_response.json()["data"]["role_ids"] == [seed_data["roles"]["viewer"]]

    target_login = _login_admin(
        client,
        seed_data["credentials"]["target_email"],
        seed_data["credentials"]["target_password"],
    )
    roles_response = client.get("/admin/roles")

    assert target_login.status_code == 200
    assert roles_response.status_code == 200


def test_department_access_helper_enforces_restriction(client: TestClient, seed_data) -> None:
    with SessionLocal() as session:
        user = UserRepository(session).get_by_id(
            seed_data["users"]["student"],
            load_relationships=True,
            include_inactive=True,
        )
        assert user is not None
        permission_service = PermissionService(session)

        assert permission_service.can_access_department(user.department_id, seed_data["departments"]["cs"], True) is True

        with pytest.raises(AuthorizationError):
            permission_service.ensure_department_access(user.department_id, seed_data["departments"]["math"], True)


def test_deactivate_role_success(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    create_response = client.post(
        "/admin/roles",
        json={
            "name": "Temporary Role",
            "code": "temporary_role",
            "description": "Created for deactivate test.",
            "is_active": True,
            "permission_ids": [seed_data["permissions"]["admin.portal.access"]],
        },
    )
    assert create_response.status_code == 200
    role_id = create_response.json()["data"]["id"]

    deactivate_response = client.post(f"/admin/roles/{role_id}/deactivate")

    assert deactivate_response.status_code == 200
    payload = deactivate_response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == role_id
    assert payload["data"]["is_active"] is False
