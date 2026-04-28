from __future__ import annotations

from fastapi.testclient import TestClient


def test_student_login_success(client: TestClient, seed_data) -> None:
    response = client.post(
        "/student/auth/login",
        json={
            "student_no": seed_data["credentials"]["student_no"],
            "password": seed_data["credentials"]["student_password"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["student_no"] == seed_data["credentials"]["student_no"]
    assert payload["user"]["department"]["code"] == "CS"


def test_student_login_failure(client: TestClient, seed_data) -> None:
    response = client.post(
        "/student/auth/login",
        json={
            "student_no": seed_data["credentials"]["student_no"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_student_me_requires_token(client: TestClient) -> None:
    response = client.get("/student/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_student_me_success(client: TestClient, seed_data) -> None:
    login_response = client.post(
        "/student/auth/login",
        json={
            "student_no": seed_data["credentials"]["student_no"],
            "password": seed_data["credentials"]["student_password"],
        },
    )
    token = login_response.json()["access_token"]

    response = client.get("/student/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Alice Student"
    assert payload["department"]["code"] == "CS"

