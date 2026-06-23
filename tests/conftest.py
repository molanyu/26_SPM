from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.core.database as database
from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import create_app
from app.modules.identity.constants import (
    ADMIN_PORTAL_ACCESS,
    IDENTITY_DEPARTMENTS_WRITE,
    IDENTITY_PERMISSIONS_READ,
    IDENTITY_ROLES_READ,
    IDENTITY_ROLES_WRITE,
    IDENTITY_USERS_WRITE,
    IDENTITY_USERS_ROLES_WRITE,
    VIOLATION_MANUAL_BLOCKS_WRITE,
)
from app.modules.identity.models.department import Department
from app.modules.identity.models.permission import Permission
from app.modules.identity.models.role import Role
from app.modules.identity.models.role_permission import RolePermission
from app.modules.identity.models.user import User
from app.modules.identity.models.user_role import UserRole


def _seed_identity_data() -> dict[str, dict[str, int] | dict[str, str]]:
    with SessionLocal() as session:
        cs_department = Department(name="Computer Science", code="CS")
        math_department = Department(name="Mathematics", code="MATH")
        session.add_all([cs_department, math_department])
        session.flush()

        permissions = [
            Permission(name="Admin Portal Access", code=ADMIN_PORTAL_ACCESS, description="Allows admin portal login."),
            Permission(name="Read Roles", code=IDENTITY_ROLES_READ, description="Allows reading roles."),
            Permission(name="Write Roles", code=IDENTITY_ROLES_WRITE, description="Allows creating and updating roles."),
            Permission(
                name="Read Permissions",
                code=IDENTITY_PERMISSIONS_READ,
                description="Allows reading permissions.",
            ),
            Permission(
                name="Create Users",
                code=IDENTITY_USERS_WRITE,
                description="Allows creating student and admin users.",
            ),
            Permission(
                name="Assign User Roles",
                code=IDENTITY_USERS_ROLES_WRITE,
                description="Allows assigning roles to users.",
            ),
            Permission(
                name="Manage Departments",
                code=IDENTITY_DEPARTMENTS_WRITE,
                description="Allows managing departments.",
            ),
            Permission(
                name="Manage Manual Reservation Blocks",
                code=VIOLATION_MANUAL_BLOCKS_WRITE,
                description="Allows manually blocking and releasing user reservation access.",
            ),
        ]
        session.add_all(permissions)
        session.flush()
        permission_ids = {permission.code: permission.id for permission in permissions}

        system_admin_role = Role(
            name="System Admin",
            code="system_admin",
            description="Full identity management access.",
            is_active=True,
        )
        viewer_role = Role(
            name="Viewer",
            code="viewer",
            description="Read-only admin access.",
            is_active=True,
        )
        operator_role = Role(
            name="Operator",
            code="operator",
            description="Admin portal access only.",
            is_active=True,
        )
        session.add_all([system_admin_role, viewer_role, operator_role])
        session.flush()

        system_admin_role.role_permissions = [RolePermission(permission=permission) for permission in permissions]
        viewer_role.role_permissions = [
            RolePermission(permission=permission)
            for permission in permissions
            if permission.code in {ADMIN_PORTAL_ACCESS, IDENTITY_ROLES_READ, IDENTITY_PERMISSIONS_READ}
        ]
        operator_role.role_permissions = [
            RolePermission(permission=permission)
            for permission in permissions
            if permission.code == ADMIN_PORTAL_ACCESS
        ]

        student_user = User(
            student_no="20240001",
            name="Alice Student",
            password_hash=hash_password("student-pass"),
            department=cs_department,
            is_active=True,
        )
        admin_user = User(
            email="admin@example.com",
            name="Root Admin",
            password_hash=hash_password("admin-pass"),
            department=cs_department,
            is_active=True,
        )
        limited_admin = User(
            email="limited@example.com",
            name="Limited Admin",
            password_hash=hash_password("limited-pass"),
            department=cs_department,
            is_active=True,
        )
        outsider = User(
            email="outsider@example.com",
            name="Outsider",
            password_hash=hash_password("outsider-pass"),
            department=math_department,
            is_active=True,
        )
        target_user = User(
            email="target@example.com",
            name="Target User",
            password_hash=hash_password("target-pass"),
            department=math_department,
            is_active=True,
        )
        session.add_all([student_user, admin_user, limited_admin, outsider, target_user])
        session.flush()

        admin_user.user_roles = [UserRole(role=system_admin_role)]
        limited_admin.user_roles = [UserRole(role=operator_role)]

        session.commit()

        return {
            "departments": {"cs": cs_department.id, "math": math_department.id},
            "permissions": permission_ids,
            "roles": {
                "system_admin": system_admin_role.id,
                "viewer": viewer_role.id,
                "operator": operator_role.id,
            },
            "users": {
                "student": student_user.id,
                "admin": admin_user.id,
                "limited_admin": limited_admin.id,
                "outsider": outsider.id,
                "target": target_user.id,
            },
            "credentials": {
                "student_no": "20240001",
                "student_password": "student-pass",
                "admin_email": "admin@example.com",
                "admin_password": "admin-pass",
                "limited_admin_email": "limited@example.com",
                "limited_admin_password": "limited-pass",
                "outsider_email": "outsider@example.com",
                "outsider_password": "outsider-pass",
                "target_email": "target@example.com",
                "target_password": "target-pass",
            },
        }


def _reset_database() -> None:
    if database.engine is None:
        raise RuntimeError("Database engine is not configured.")
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret_key="test-secret",
        admin_session_cookie_name="test_admin_session",
    )
    app = create_app(settings)
    _reset_database()
    with TestClient(app) as test_client:
        test_client.app.state.seed_data = _seed_identity_data()
        yield test_client


@pytest.fixture
def seed_data(client: TestClient):
    return client.app.state.seed_data
