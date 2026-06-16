from __future__ import annotations

from fastapi.testclient import TestClient


def _login_admin(client: TestClient, *, email: str, password: str) -> None:
    response = client.post(
        "/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def test_admin_can_query_system_configs(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.get("/admin/system-configs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 6
    returned = {item["config_key"]: item["config_value"] for item in payload["items"]}
    assert returned["max_reservation_hours"] == 4
    assert returned["checkin_grace_minutes"] == 10
    assert returned["violation_threshold_minutes"] == 15
    assert returned["violation_penalty_threshold_count"] == 3
    assert returned["violation_penalty_window_days"] == 30
    assert returned["violation_penalty_duration_days"] == 7


def test_admin_can_update_max_reservation_hours(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/max_reservation_hours",
        json={"config_value": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["config_key"] == "max_reservation_hours"
    assert payload["data"]["config_value"] == 6


def test_admin_can_update_checkin_grace_minutes(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/checkin_grace_minutes",
        json={"config_value": 12},
    )

    assert response.status_code == 200
    assert response.json()["data"]["config_value"] == 12


def test_admin_can_update_violation_threshold_minutes(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/violation_threshold_minutes",
        json={"config_value": 18},
    )

    assert response.status_code == 200
    assert response.json()["data"]["config_value"] == 18


def test_admin_can_update_violation_penalty_configs(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    updates = {
        "violation_penalty_threshold_count": 4,
        "violation_penalty_window_days": 45,
        "violation_penalty_duration_days": 10,
    }

    for config_key, value in updates.items():
        response = client.put(
            f"/admin/system-configs/{config_key}",
            json={"config_value": value},
        )

        assert response.status_code == 200
        assert response.json()["data"]["config_key"] == config_key
        assert response.json()["data"]["config_value"] == value


def test_unauthenticated_access_to_system_config_endpoints_fails(client: TestClient):
    list_response = client.get("/admin/system-configs")
    assert list_response.status_code == 401
    assert list_response.json()["code"] == "unauthenticated"

    update_response = client.put(
        "/admin/system-configs/max_reservation_hours",
        json={"config_value": 6},
    )
    assert update_response.status_code == 401
    assert update_response.json()["code"] == "unauthenticated"


def test_limited_admin_cannot_read_or_update_system_configs(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["limited_admin_email"],
        password=seed_data["credentials"]["limited_admin_password"],
    )

    list_response = client.get("/admin/system-configs")
    assert list_response.status_code == 403
    assert list_response.json()["code"] == "forbidden"

    update_response = client.put(
        "/admin/system-configs/max_reservation_hours",
        json={"config_value": 6},
    )
    assert update_response.status_code == 403
    assert update_response.json()["code"] == "forbidden"


def test_invalid_config_key_update_fails(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/unknown_key",
        json={"config_value": 6},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_invalid_type_update_fails(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/max_reservation_hours",
        json={"config_value": True},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_invalid_range_update_fails(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    response = client.put(
        "/admin/system-configs/max_reservation_hours",
        json={"config_value": 0},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_violation_penalty_configs_must_be_positive_integers(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    for config_key in [
        "violation_penalty_threshold_count",
        "violation_penalty_window_days",
        "violation_penalty_duration_days",
    ]:
        response = client.put(
            f"/admin/system-configs/{config_key}",
            json={"config_value": 0},
        )

        assert response.status_code == 400
        assert response.json()["code"] == "bad_request"


def test_violation_threshold_cannot_be_lower_than_checkin_grace(client: TestClient, seed_data: dict):
    _login_admin(
        client,
        email=seed_data["credentials"]["admin_email"],
        password=seed_data["credentials"]["admin_password"],
    )

    setup_response = client.put(
        "/admin/system-configs/checkin_grace_minutes",
        json={"config_value": 12},
    )
    assert setup_response.status_code == 200

    response = client.put(
        "/admin/system-configs/violation_threshold_minutes",
        json={"config_value": 11},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
