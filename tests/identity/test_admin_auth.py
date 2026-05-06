from __future__ import annotations

from fastapi.testclient import TestClient


def _login_admin(client: TestClient, email: str, password: str):
    return client.post("/admin/auth/login", json={"email": email, "password": password})


def test_admin_login_success_sets_session_cookie(client: TestClient, seed_data) -> None:
    response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["user"]["email"] == seed_data["credentials"]["admin_email"]
    assert client.cookies.get("test_admin_session")


def test_admin_login_rejects_user_without_admin_permission(client: TestClient, seed_data) -> None:
    response = _login_admin(
        client,
        seed_data["credentials"]["outsider_email"],
        seed_data["credentials"]["outsider_password"],
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_admin_me_returns_permissions_and_filtered_menus(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["limited_admin_email"],
        seed_data["credentials"]["limited_admin_password"],
    )
    assert login_response.status_code == 200

    response = client.get("/admin/me")

    assert response.status_code == 200
    payload = response.json()
    assert [permission["code"] for permission in payload["permissions"]] == ["admin.portal.access"]
    assert payload["menus"] == [
        {"code": "admin.dashboard", "label": "管理首页"},
        {"code": "reservation.records", "label": "预约记录"},
        {"code": "reservation.actions", "label": "代理预约"},
        {"code": "checkin.records", "label": "动态签到码"},
        {"code": "notification.logs", "label": "通知日志"},
    ]


def test_admin_logout_clears_session(client: TestClient, seed_data) -> None:
    login_response = _login_admin(
        client,
        seed_data["credentials"]["admin_email"],
        seed_data["credentials"]["admin_password"],
    )
    assert login_response.status_code == 200

    logout_response = client.post("/admin/auth/logout")
    protected_response = client.get("/admin/me")

    assert logout_response.status_code == 200
    assert protected_response.status_code == 401
    assert protected_response.json()["code"] == "unauthenticated"
