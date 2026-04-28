from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from urllib.parse import urlencode

import app.core.database as database
from app.core.config import Settings
from app.core.database import SessionLocal
from app.main import create_app
from app.modules.identity.constants import DEFAULT_PERMISSION_CODES, SYSTEM_ADMIN_ROLE_CODE
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission
from app.modules.identity.models.user import User
from app.modules.identity.services.bootstrap_service import BootstrapService


def _reset_database() -> None:
    if database.engine is None:
        raise RuntimeError("Database engine is not configured.")
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)


def test_startup_bootstrap_allows_first_admin_login() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret_key="bootstrap-secret",
        admin_session_cookie_name="bootstrap_session",
        identity_bootstrap_enabled=True,
        identity_bootstrap_admin_email="bootstrap@example.com",
        identity_bootstrap_admin_name="Bootstrap Admin",
        identity_bootstrap_admin_password="bootstrap-pass",
    )
    app = create_app(settings)
    _reset_database()

    with TestClient(app) as client:
        login_response = client.post(
            "/admin/auth/login",
            json={"email": "bootstrap@example.com", "password": "bootstrap-pass"},
        )

        assert login_response.status_code == 200
        assert client.cookies.get("bootstrap_session")

        with SessionLocal() as session:
            permission_codes = {permission.code for permission in session.scalars(select(Permission))}
            bootstrap_role = session.scalar(
                select(Role)
                .where(Role.code == SYSTEM_ADMIN_ROLE_CODE)
                .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            )
            bootstrap_user = session.scalar(select(User).where(User.email == "bootstrap@example.com"))

        assert set(DEFAULT_PERMISSION_CODES).issubset(permission_codes)
        assert bootstrap_role is not None
        assert {item.permission.code for item in bootstrap_role.role_permissions if item.permission is not None} == set(
            DEFAULT_PERMISSION_CODES
        )
        assert bootstrap_user is not None


def test_startup_bootstrap_admin_can_use_browser_login_flow() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret_key="bootstrap-secret",
        admin_session_cookie_name="bootstrap_session",
        identity_bootstrap_enabled=True,
        identity_bootstrap_admin_email="bootstrap@example.com",
        identity_bootstrap_admin_name="Bootstrap Admin",
        identity_bootstrap_admin_password="bootstrap-pass",
    )
    app = create_app(settings)
    _reset_database()

    with TestClient(app) as client:
        login_page = client.get("/admin/login", headers={"accept": "text/html"})
        assert login_page.status_code == 200

        login_response = client.post(
            "/admin/login",
            content=urlencode(
                {
                    "email": "bootstrap@example.com",
                    "password": "bootstrap-pass",
                    "next": "/admin",
                }
            ),
            headers={
                "accept": "text/html",
                "content-type": "application/x-www-form-urlencoded",
            },
            follow_redirects=False,
        )

        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/admin"
        assert client.cookies.get("bootstrap_session")


def test_bootstrap_is_idempotent() -> None:
    settings = Settings(database_url="sqlite:///:memory:")
    app = create_app(settings)
    _reset_database()

    with TestClient(app):
        with SessionLocal() as session:
            service = BootstrapService(session)
            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )
            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )

            permission_count = session.scalar(select(func.count(Permission.id)))
            role_count = session.scalar(select(func.count(Role.id)).where(Role.code == SYSTEM_ADMIN_ROLE_CODE))
            user_count = session.scalar(select(func.count(User.id)).where(User.email == "bootstrap@example.com"))

        assert permission_count == len(DEFAULT_PERMISSION_CODES)
        assert role_count == 1
        assert user_count == 1


def test_bootstrap_does_not_reactivate_disabled_system_admin_role() -> None:
    settings = Settings(database_url="sqlite:///:memory:")
    app = create_app(settings)
    _reset_database()

    with TestClient(app):
        with SessionLocal() as session:
            service = BootstrapService(session)
            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )

            role = session.scalar(select(Role).where(Role.code == SYSTEM_ADMIN_ROLE_CODE))
            assert role is not None
            role.is_active = False
            session.add(role)
            session.commit()

            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )
            session.expire_all()
            persisted_role = session.scalar(select(Role).where(Role.code == SYSTEM_ADMIN_ROLE_CODE))

        assert persisted_role is not None
        assert persisted_role.is_active is False


def test_bootstrap_does_not_mutate_existing_system_admin_permissions() -> None:
    settings = Settings(database_url="sqlite:///:memory:")
    app = create_app(settings)
    _reset_database()

    with TestClient(app):
        with SessionLocal() as session:
            service = BootstrapService(session)
            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )

            role = session.scalar(
                select(Role)
                .where(Role.code == SYSTEM_ADMIN_ROLE_CODE)
                .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            )
            assert role is not None

            kept_permission = next(
                item.permission
                for item in role.role_permissions
                if item.permission is not None and item.permission.code == "admin.portal.access"
            )
            for role_permission in list(role.role_permissions):
                if role_permission.permission_id != kept_permission.id:
                    role.role_permissions.remove(role_permission)
            session.add(role)
            session.commit()

            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )
            session.expire_all()
            persisted_role = session.scalar(
                select(Role)
                .where(Role.code == SYSTEM_ADMIN_ROLE_CODE)
                .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            )

        assert persisted_role is not None
        assert {item.permission.code for item in persisted_role.role_permissions if item.permission is not None} == {
            "admin.portal.access"
        }


def test_bootstrap_does_not_reactivate_disabled_bootstrap_admin_user() -> None:
    settings = Settings(database_url="sqlite:///:memory:")
    app = create_app(settings)
    _reset_database()

    with TestClient(app):
        with SessionLocal() as session:
            service = BootstrapService(session)
            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )

            admin_user = session.scalar(select(User).where(User.email == "bootstrap@example.com"))
            assert admin_user is not None
            admin_user.is_active = False
            session.add(admin_user)
            session.commit()

            service.bootstrap(
                admin_email="bootstrap@example.com",
                admin_name="Bootstrap Admin",
                admin_password="bootstrap-pass",
            )
            session.expire_all()
            persisted_user = session.scalar(select(User).where(User.email == "bootstrap@example.com"))

        assert persisted_user is not None
        assert persisted_user.is_active is False


def test_startup_does_not_bootstrap_when_disabled() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        identity_bootstrap_enabled=False,
        identity_bootstrap_admin_email="bootstrap@example.com",
        identity_bootstrap_admin_name="Bootstrap Admin",
        identity_bootstrap_admin_password="bootstrap-pass",
    )
    app = create_app(settings)
    _reset_database()

    with TestClient(app):
        with SessionLocal() as session:
            permission_count = session.scalar(select(func.count(Permission.id)))
            role_count = session.scalar(select(func.count(Role.id)))
            user_count = session.scalar(select(func.count(User.id)))

        assert permission_count == 0
        assert role_count == 0
        assert user_count == 0
