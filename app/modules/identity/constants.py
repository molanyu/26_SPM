from __future__ import annotations

ADMIN_PORTAL_ACCESS = "admin.portal.access"
IDENTITY_ROLES_READ = "identity.roles.read"
IDENTITY_ROLES_WRITE = "identity.roles.write"
IDENTITY_PERMISSIONS_READ = "identity.permissions.read"
IDENTITY_USERS_WRITE = "identity.users.write"
IDENTITY_USERS_ROLES_WRITE = "identity.users.roles.write"
IDENTITY_DEPARTMENTS_WRITE = "identity.departments.write"
VIOLATION_MANUAL_BLOCKS_WRITE = "violation.manual_blocks.write"
SYSTEM_ADMIN_ROLE_CODE = "system_admin"
SYSTEM_ADMIN_ROLE_NAME = "System Admin"

BASE_PERMISSION_DEFINITIONS = [
    {
        "name": "后台访问",
        "code": ADMIN_PORTAL_ACCESS,
        "description": "允许登录并访问管理后台。",
    },
    {
        "name": "查看角色",
        "code": IDENTITY_ROLES_READ,
        "description": "允许查看角色及其权限配置。",
    },
    {
        "name": "维护角色",
        "code": IDENTITY_ROLES_WRITE,
        "description": "允许创建、更新和停用角色。",
    },
    {
        "name": "查看权限参考",
        "code": IDENTITY_PERMISSIONS_READ,
        "description": "允许查看权限清单及用途说明。",
    },
    {
        "name": "创建用户账号",
        "code": IDENTITY_USERS_WRITE,
        "description": "允许创建单个学生账号或管理员账号。",
    },
    {
        "name": "分配用户角色",
        "code": IDENTITY_USERS_ROLES_WRITE,
        "description": "允许调整指定用户的角色集合。",
    },
    {
        "name": "维护院系",
        "code": IDENTITY_DEPARTMENTS_WRITE,
        "description": "允许查看、新增、启用和停用院系。",
    },
    {
        "name": "维护手动预约限制",
        "code": VIOLATION_MANUAL_BLOCKS_WRITE,
        "description": "允许管理员手动开启和解除指定用户的预约限制。",
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
        "code": "reservation.records",
        "label": "预约记录",
        "required_permissions": [ADMIN_PORTAL_ACCESS],
    },
    {
        "code": "reservation.actions",
        "label": "代理预约",
        "required_permissions": [ADMIN_PORTAL_ACCESS],
    },
    {
        "code": "checkin.records",
        "label": "动态签到码",
        "required_permissions": [ADMIN_PORTAL_ACCESS],
    },
    {
        "code": "identity.roles",
        "label": "角色管理",
        "required_permissions": [IDENTITY_ROLES_READ],
    },
    {
        "code": "identity.users.create",
        "label": "创建用户",
        "required_permissions": [IDENTITY_USERS_WRITE],
    },
    {
        "code": "identity.departments",
        "label": "院系管理",
        "required_permissions": [IDENTITY_DEPARTMENTS_WRITE],
    },
    {
        "code": "identity.permissions",
        "label": "权限参考",
        "required_permissions": [IDENTITY_ROLES_READ, IDENTITY_PERMISSIONS_READ],
    },
    {
        "code": "identity.user_roles",
        "label": "用户角色分配",
        "required_permissions": [IDENTITY_ROLES_READ, IDENTITY_USERS_ROLES_WRITE],
    },
    {
        "code": "statistics.usage",
        "label": "统计查询",
        "required_permissions": [IDENTITY_PERMISSIONS_READ],
    },
    {
        "code": "violation.records",
        "label": "违约记录",
        "required_permissions": [IDENTITY_PERMISSIONS_READ],
    },
    {
        "code": "notification.logs",
        "label": "通知日志",
        "required_permissions": [ADMIN_PORTAL_ACCESS],
    },
]
