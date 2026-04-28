from __future__ import annotations

from datetime import date

from fastapi import Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.services.menu_service import AdminPortalMenuService
from app.core.errors import AppError
from app.modules.identity.models.role import Role
from app.modules.identity.models.user import User
from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import RoleRead
from app.modules.identity.services.permission_service import PermissionService
from app.modules.resource.schemas.room import AdminRoomRead
from app.modules.resource.schemas.seat import AdminSeatRead
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.schemas.config import SystemConfigRead
from app.modules.system_config.services.config_service import ConfigService
from app.modules.violation.schemas.violation import ViolationQueryFilters
from app.modules.violation.services.query_service import QueryService


def prefers_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


class AdminPageService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.permission_service = PermissionService(session)
        self.room_service = RoomService(session)
        self.seat_service = SeatService(session)
        self.config_service = ConfigService(session)
        self.query_service = QueryService(session)
        self.menu_service = AdminPortalMenuService()

    def build_base_context(
        self,
        request: Request,
        current_admin: User,
        *,
        page_title: str,
        page_key: str,
        error_message: str | None = None,
        success_message: str | None = None,
        **content: object,
    ) -> dict[str, object]:
        navigation = self.menu_service.build_navigation(current_admin.id, self.permission_service)
        return {
            "request": request,
            "current_admin": current_admin,
            "page_title": page_title,
            "page_key": page_key,
            "error_message": error_message,
            "success_message": success_message,
            **navigation,
            **content,
        }

    def get_home_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        return self.build_base_context(
            request,
            current_admin,
            page_title="管理首页",
            page_key="admin.dashboard",
            error_message=error_message,
            success_message=success_message,
            hero_title="后台入口",
            hero_description="通过权限控制的服务端渲染页面访问已交付业务模块。",
        )

    def list_roles_payload(self) -> dict[str, object]:
        roles = [self._build_role_read(role).model_dump() for role in self.permission_service.list_roles()]
        return {
            "items": roles,
            "total": len(roles),
            "page": 1,
            "page_size": len(roles),
        }

    def list_permissions_payload(self) -> dict[str, object]:
        permissions = [PermissionRead.model_validate(permission).model_dump() for permission in self.permission_service.list_permissions()]
        return {
            "items": permissions,
            "total": len(permissions),
            "page": 1,
            "page_size": len(permissions),
        }

    def get_roles_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        create_form = create_form or {
            "name": "",
            "code": "",
            "description": "",
            "is_active": True,
            "permission_ids": [],
        }
        return self.build_base_context(
            request,
            current_admin,
            page_title="角色管理",
            page_key="identity.roles",
            error_message=error_message,
            success_message=success_message,
            roles=self.list_roles_payload()["items"],
            permissions=self.list_permissions_payload()["items"],
            create_form=create_form,
        )

    def get_user_roles_context(
        self,
        request: Request,
        current_admin: User,
        *,
        user_id: int,
        selected_role_ids: list[int] | None = None,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        selected_role_ids = selected_role_ids or []
        return self.build_base_context(
            request,
            current_admin,
            page_title="用户角色分配",
            page_key="identity.user_roles",
            error_message=error_message,
            success_message=success_message,
            target_user_id=user_id,
            roles=self.list_roles_payload()["items"],
            selected_role_ids=selected_role_ids,
        )

    def list_rooms_payload(self) -> dict[str, object]:
        return self.room_service.list_admin_rooms()

    def get_rooms_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        create_form = create_form or {
            "name": "",
            "location": "",
            "department_id": "",
            "is_department_only": False,
            "is_active": True,
            "open_time": "08:00",
            "close_time": "22:00",
        }
        return self.build_base_context(
            request,
            current_admin,
            page_title="自习室管理",
            page_key="resource.rooms",
            error_message=error_message,
            success_message=success_message,
            rooms=self.list_rooms_payload()["items"],
            create_form=create_form,
        )

    def list_seats_payload(self, room_id: int | None = None) -> dict[str, object]:
        return self.seat_service.list_admin_seats(room_id=room_id)

    def get_seats_context(
        self,
        request: Request,
        current_admin: User,
        *,
        room_id: int | None = None,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        rooms = self.list_rooms_payload()["items"]
        create_form = create_form or {
            "room_id": str(room_id or ""),
            "seat_code": "",
            "seat_label": "",
            "is_active": True,
            "is_window_side": False,
            "has_power_socket": False,
            "has_track_socket": False,
        }
        return self.build_base_context(
            request,
            current_admin,
            page_title="座位管理",
            page_key="resource.seats",
            error_message=error_message,
            success_message=success_message,
            seats=self.list_seats_payload(room_id=room_id)["items"],
            rooms=rooms,
            selected_room_id=room_id,
            create_form=create_form,
        )

    def list_system_configs_payload(self) -> dict[str, object]:
        items = [self._build_config_read(config).model_dump() for config in self.config_service.list_configs()]
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": len(items),
        }

    def get_system_configs_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        return self.build_base_context(
            request,
            current_admin,
            page_title="系统参数管理",
            page_key="system.configs",
            error_message=error_message,
            success_message=success_message,
            configs=self.list_system_configs_payload()["items"],
        )

    def get_reservation_actions_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_result: dict[str, object] | None = None,
        cancel_result: dict[str, object] | None = None,
        create_form: dict[str, object] | None = None,
        cancel_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.build_base_context(
            request,
            current_admin,
            page_title="代理预约与代取消",
            page_key="reservation.actions",
            error_message=error_message,
            success_message=success_message,
            create_result=create_result,
            cancel_result=cancel_result,
            create_form=create_form
            or {
                "user_id": "",
                "seat_id": "",
                "start_time": "",
                "end_time": "",
            },
            cancel_form=cancel_form
            or {
                "reservation_id": "",
                "reason": "",
            },
        )

    def list_violations_payload(self, filters: ViolationQueryFilters) -> dict[str, object]:
        result = self.query_service.list_records(filters)
        return {
            "items": [item.model_dump() for item in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    def get_violations_context(
        self,
        request: Request,
        current_admin: User,
        *,
        user_id: int | None = None,
        room_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        filters = ViolationQueryFilters(
            user_id=user_id,
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        payload = self.list_violations_payload(filters)
        return self.build_base_context(
            request,
            current_admin,
            page_title="违约记录查询",
            page_key="violation.records",
            error_message=error_message,
            success_message=success_message,
            violations=payload["items"],
            total=payload["total"],
            filters=filters.model_dump(),
        )

    def format_exception_message(self, exc: Exception) -> str:
        if isinstance(exc, AppError):
            return exc.message
        if isinstance(exc, ValidationError):
            return "; ".join(error["msg"] for error in exc.errors())
        return str(exc)

    def html_error_status(self, exc: Exception) -> int:
        if isinstance(exc, AppError):
            return exc.status_code
        return 400

    def _build_role_read(self, role: Role) -> RoleRead:
        permissions = [
            PermissionRead.model_validate(role_permission.permission)
            for role_permission in sorted(role.role_permissions, key=lambda item: item.permission_id)
        ]
        return RoleRead(
            id=role.id,
            name=role.name,
            code=role.code,
            description=role.description,
            is_active=role.is_active,
            permissions=permissions,
        )

    def _build_config_read(self, config: SystemConfig) -> SystemConfigRead:
        return SystemConfigRead(
            id=config.id,
            config_key=config.config_key,
            config_value=self.config_service.parse_config_value(config),
            value_type=config.value_type,
            description=config.description,
            updated_at=config.updated_at,
        )
