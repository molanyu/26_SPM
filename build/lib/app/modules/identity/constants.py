from __future__ import annotations

ADMIN_PORTAL_ACCESS = "admin.portal.access"
IDENTITY_ROLES_READ = "identity.roles.read"
IDENTITY_ROLES_WRITE = "identity.roles.write"
IDENTITY_PERMISSIONS_READ = "identity.permissions.read"
IDENTITY_USERS_ROLES_WRITE = "identity.users.roles.write"
SYSTEM_ADMIN_ROLE_CODE = "system_admin"
SYSTEM_ADMIN_ROLE_NAME = "System Admin"

BASE_PERMISSION_DEFINITIONS = [
    {
        "name": "Admin Portal Access",
        "code": ADMIN_PORTAL_ACCESS,
        "description": "Allows admin portal login.",
    },
    {
        "name": "Read Roles",
        "code": IDENTITY_ROLES_READ,
        "description": "Allows reading roles.",
    },
    {
        "name": "Write Roles",
        "code": IDENTITY_ROLES_WRITE,
        "description": "Allows creating and updating roles.",
    },
    {
        "name": "Read Permissions",
        "code": IDENTITY_PERMISSIONS_READ,
        "description": "Allows reading permissions.",
    },
    {
        "name": "Assign User Roles",
        "code": IDENTITY_USERS_ROLES_WRITE,
        "description": "Allows assigning roles to users.",
    },
]

DEFAULT_PERMISSION_CODES = [definition["code"] for definition in BASE_PERMISSION_DEFINITIONS]

MENU_DEFINITIONS = [
    {
        "code": "admin.dashboard",
        "label": "管理首页",
        "required_permissions": [ADMIN_PORTAL_ACCESS],
    },
    {
        "code": "identity.roles",
        "label": "角色管理",
        "required_permissions": [IDENTITY_ROLES_READ],
    },
    {
        "code": "identity.permissions",
        "label": "权限点列表",
        "required_permissions": [IDENTITY_PERMISSIONS_READ],
    },
    {
        "code": "identity.user_roles",
        "label": "用户角色分配",
        "required_permissions": [IDENTITY_USERS_ROLES_WRITE],
    },
]
