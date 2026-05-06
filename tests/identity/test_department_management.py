from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.identity.models.department import Department


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def test_admin_can_create_list_activate_and_deactivate_department(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    create_response = client.post(
        "/admin/departments",
        json={
            "name": "Engineering Department",
            "code": "ENG",
            "is_active": True,
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()["data"]
    department_id = created["id"]
    assert created["name"] == "Engineering Department"
    assert created["code"] == "ENG"
    assert created["is_active"] is True

    list_response = client.get("/admin/departments")
    assert list_response.status_code == 200
    assert any(item["id"] == department_id for item in list_response.json()["items"])

    deactivate_response = client.post(f"/admin/departments/{department_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["data"]["is_active"] is False

    activate_response = client.post(f"/admin/departments/{department_id}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["data"]["is_active"] is True


def test_department_create_rejects_duplicate_name_or_code(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )
    create_response = client.post(
        "/admin/departments",
        json={
            "name": "Duplicate Department",
            "code": "DUP",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200

    duplicate_name = client.post(
        "/admin/departments",
        json={
            "name": "Duplicate Department",
            "code": "DUP2",
            "is_active": True,
        },
    )
    assert duplicate_name.status_code == 409
    assert duplicate_name.json()["code"] == "conflict"
    assert duplicate_name.json()["details"]["field"] == "name"

    duplicate_code = client.post(
        "/admin/departments",
        json={
            "name": "Duplicate Department 2",
            "code": "DUP",
            "is_active": True,
        },
    )
    assert duplicate_code.status_code == 409
    assert duplicate_code.json()["code"] == "conflict"
    assert duplicate_code.json()["details"]["field"] == "code"


def test_department_management_requires_department_write_permission(
    client: TestClient,
    seed_data: dict,
) -> None:
    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )

    list_response = client.get("/admin/departments")
    assert list_response.status_code == 403
    assert list_response.json()["code"] == "forbidden"

    create_response = client.post(
        "/admin/departments",
        json={
            "name": "Blocked Department",
            "code": "BLOCKED",
            "is_active": True,
        },
    )
    assert create_response.status_code == 403
    assert create_response.json()["code"] == "forbidden"

    with SessionLocal() as session:
        department = session.scalar(select(Department).where(Department.code == "BLOCKED"))
        assert department is None
