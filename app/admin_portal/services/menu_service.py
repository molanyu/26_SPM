from __future__ import annotations

from dataclasses import dataclass

from app.modules.identity.constants import (
    ADMIN_PORTAL_ACCESS,
    IDENTITY_PERMISSIONS_READ,
    IDENTITY_ROLES_READ,
    IDENTITY_USERS_ROLES_WRITE,
    IDENTITY_USERS_WRITE,
)
from app.modules.identity.services.menu_service import MenuService as IdentityMenuService
from app.modules.identity.services.permission_service import PermissionService


@dataclass(frozen=True, slots=True)
class ShortcutDefinition:
    code: str
    label: str
    description: str
    href: str
    required_permissions: tuple[str, ...]


class AdminPortalMenuService:
    _MENU_HREFS = {
        "admin.dashboard": "/admin",
        "reservation.records": "/admin/reservations/records",
        "reservation.actions": "/admin/reservations/actions",
        "identity.roles": "/admin/roles",
        "identity.users.create": "/admin/users/new",
        "identity.permissions": "/admin/roles#permission-reference",
        "identity.user_roles": "/admin/roles#user-role-entry",
        "statistics.usage": "/admin/statistics",
        "violation.records": "/admin/violations",
    }

    _SHORTCUTS = (
        ShortcutDefinition(
            code="identity.roles",
            label="角色管理",
            description="查看角色现状、整理权限组合，并进入独立编辑区。",
            href="/admin/roles",
            required_permissions=(IDENTITY_ROLES_READ,),
        ),
        ShortcutDefinition(
            code="identity.users.create",
            label="创建用户",
            description="创建单个学生账号或管理员账号，并继续处理后续授权。",
            href="/admin/users/new",
            required_permissions=(IDENTITY_USERS_WRITE,),
        ),
        ShortcutDefinition(
            code="identity.user_roles",
            label="用户角色分配",
            description="从角色页进入用户角色分配入口，先定位用户再调整角色。",
            href="/admin/roles#user-role-entry",
            required_permissions=(IDENTITY_ROLES_READ, IDENTITY_USERS_ROLES_WRITE),
        ),
        ShortcutDefinition(
            code="resource.rooms",
            label="自习室管理",
            description="查看、创建、修改和停用自习室。",
            href="/admin/rooms",
            required_permissions=(ADMIN_PORTAL_ACCESS,),
        ),
        ShortcutDefinition(
            code="resource.seats",
            label="座位管理",
            description="查看、创建、修改和停用座位。",
            href="/admin/seats",
            required_permissions=(ADMIN_PORTAL_ACCESS,),
        ),
        ShortcutDefinition(
            code="reservation.records",
            label="预约记录查询",
            description="按用户、房间、座位、状态和日期范围查询预约记录。",
            href="/admin/reservations/records",
            required_permissions=(ADMIN_PORTAL_ACCESS,),
        ),
        ShortcutDefinition(
            code="reservation.actions",
            label="代理预约与取消",
            description="提交管理员代预约和代取消操作。",
            href="/admin/reservations/actions",
            required_permissions=(ADMIN_PORTAL_ACCESS,),
        ),
        ShortcutDefinition(
            code="statistics.usage",
            label="统计查询",
            description="查看使用率与违约率统计结果。",
            href="/admin/statistics",
            required_permissions=(IDENTITY_PERMISSIONS_READ,),
        ),
        ShortcutDefinition(
            code="system.configs",
            label="系统参数管理",
            description="查看和更新系统参数。",
            href="/admin/system-configs",
            required_permissions=(IDENTITY_PERMISSIONS_READ,),
        ),
        ShortcutDefinition(
            code="violation.records",
            label="违约记录查询",
            description="按条件查询违约记录。",
            href="/admin/violations",
            required_permissions=(IDENTITY_PERMISSIONS_READ,),
        ),
    )

    def build_navigation(self, user_id: int, permission_service: PermissionService) -> dict[str, object]:
        permissions = permission_service.get_user_permissions(user_id)
        permission_codes = {permission.code for permission in permissions}
        menus = []
        for menu in IdentityMenuService().build_menus(permission_codes):
            menus.append(
                {
                    "code": menu["code"],
                    "label": menu["label"],
                    "href": self._MENU_HREFS.get(menu["code"], "/admin"),
                }
            )
        shortcuts = [
            {
                "code": shortcut.code,
                "label": shortcut.label,
                "description": shortcut.description,
                "href": shortcut.href,
            }
            for shortcut in self._SHORTCUTS
            if set(shortcut.required_permissions).issubset(permission_codes)
        ]
        return {
            "permission_codes": permission_codes,
            "menus": menus,
            "shortcuts": shortcuts,
        }
