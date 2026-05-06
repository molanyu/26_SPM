from __future__ import annotations

from datetime import date, time as time_value

from fastapi import Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.admin_portal.services.menu_service import AdminPortalMenuService
from app.core.errors import AppError
from app.modules.checkin.services.admin_checkin_service import AdminCheckinService
from app.modules.identity.constants import IDENTITY_USERS_ROLES_WRITE
from app.modules.identity.models.role import Role
from app.modules.identity.models.user import User
from app.modules.identity.schemas.department import DepartmentRead as ManagedDepartmentRead
from app.modules.identity.schemas.permission import PermissionRead
from app.modules.identity.schemas.role import RoleRead
from app.modules.identity.schemas.user import DepartmentRead, UserCreateResult
from app.modules.identity.services.department_service import DepartmentService
from app.modules.identity.services.permission_service import PermissionService
from app.modules.identity.services.user_service import UserService
from app.modules.notification.services.admin_notification_service import AdminNotificationService
from app.modules.reservation.schemas.reservation import AdminReservationQueryFilters
from app.modules.reservation.services.query_service import ReservationQueryService
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.schemas.config import SystemConfigRead
from app.modules.system_config.services.config_service import ConfigService
from app.modules.resource.services.room_service import RoomService
from app.modules.resource.services.seat_service import SeatService
from app.modules.violation.schemas.statistics import StatisticsQueryFilters
from app.modules.violation.schemas.violation import ViolationQueryFilters
from app.modules.violation.services.query_service import QueryService
from app.modules.violation.services.statistics_service import StatisticsService

_PERMISSION_UI_COPY = {
    "admin.portal.access": {
        "name": "后台访问",
        "description": "允许登录并进入管理后台。",
    },
    "identity.roles.read": {
        "name": "查看角色",
        "description": "允许查看角色列表、角色详情和权限组合。",
    },
    "identity.roles.write": {
        "name": "维护角色",
        "description": "允许创建角色并调整角色配置。",
    },
    "identity.permissions.read": {
        "name": "查看权限参考",
        "description": "允许查看权限清单及用途说明。",
    },
    "identity.users.write": {
        "name": "创建用户账号",
        "description": "允许创建单个学生账号或管理员账号。",
    },
    "identity.users.roles.write": {
        "name": "分配用户角色",
        "description": "允许替换指定用户的角色集合。",
    },
    "identity.departments.write": {
        "name": "维护院系",
        "description": "允许查看、新增、启用和停用院系。",
    },
}


def prefers_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


class AdminPageService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.permission_service = PermissionService(session)
        self.user_service = UserService(session)
        self.department_service = DepartmentService(session)
        self.room_service = RoomService(session)
        self.seat_service = SeatService(session)
        self.config_service = ConfigService(session)
        self.reservation_query_service = ReservationQueryService(session)
        self.admin_checkin_service = AdminCheckinService(session)
        self.admin_notification_service = AdminNotificationService(session)
        self.query_service = QueryService(session)
        self.statistics_service = StatisticsService(session)
        self.menu_service = AdminPortalMenuService()

    def build_base_context(
        self,
        request: Request,
        current_admin: User,
        *,
        page_title: str,
        page_key: str,
        page_intro: str | None = None,
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
            "page_intro": page_intro or "",
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
            page_intro="保持现有会话、权限和路由机制不变，从这里进入后台各项管理任务。",
            error_message=error_message,
            success_message=success_message,
            hero_title="今天要先处理哪项后台任务？",
            hero_description="首页入口会按当前账号权限自动裁剪，你可以从这里进入角色、资源、系统参数、预约和违约记录等页面。",
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
        permissions = [
            PermissionRead.model_validate(permission).model_dump()
            for permission in self.permission_service.list_permissions()
        ]
        return {
            "items": permissions,
            "total": len(permissions),
            "page": 1,
            "page_size": len(permissions),
        }

    def list_departments_payload(self) -> dict[str, object]:
        departments = [
            ManagedDepartmentRead.model_validate(department).model_dump()
            for department in self.department_service.list_departments()
        ]
        return {
            "items": departments,
            "total": len(departments),
            "page": 1,
            "page_size": len(departments),
        }

    def get_roles_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
        edit_role_id: int | None = None,
        edit_form: dict[str, object] | None = None,
        target_lookup_value: str = "",
    ) -> dict[str, object]:
        roles = self._decorate_roles(self.list_roles_payload()["items"])
        permissions = self._decorate_permissions(self.list_permissions_payload()["items"])
        normalized_create_form = self._normalize_role_form(
            create_form
            or {
                "name": "",
                "code": "",
                "description": "",
                "is_active": True,
                "permission_ids": [],
            }
        )
        selected_role = next((role for role in roles if role["id"] == edit_role_id), None) if edit_role_id is not None else None
        normalized_edit_form = self._normalize_role_form(edit_form) if edit_form is not None else None
        if normalized_edit_form is None and selected_role is not None:
            normalized_edit_form = self._normalize_role_form(selected_role)

        return self.build_base_context(
            request,
            current_admin,
            page_title="角色管理",
            page_key="identity.roles",
            page_intro="先看清当前角色与权限组合，再进入独立编辑区或为指定用户分配角色，避免在列表里直接做高密度编辑。",
            error_message=error_message,
            success_message=success_message,
            roles=roles,
            permissions=permissions,
            create_form=normalized_create_form,
            edit_form=normalized_edit_form,
            selected_role_id=edit_role_id,
            selected_role_missing=edit_role_id is not None and selected_role is None and normalized_edit_form is None,
            target_lookup_value=target_lookup_value,
            role_count=len(roles),
            active_role_count=sum(1 for role in roles if role["is_active"]),
            inactive_role_count=sum(1 for role in roles if not role["is_active"]),
            permission_count=len(permissions),
        )

    def get_departments_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        departments = self._decorate_departments(self.list_departments_payload()["items"])
        normalized_form = self._normalize_department_form(
            create_form
            or {
                "name": "",
                "code": "",
                "is_active": True,
            }
        )
        return self.build_base_context(
            request,
            current_admin,
            page_title="院系管理",
            page_key="identity.departments",
            page_intro="维护最小院系基础数据，供用户创建和院系专属自习室选择使用。",
            error_message=error_message,
            success_message=success_message,
            departments=departments,
            create_form=normalized_form,
            department_count=len(departments),
            active_department_count=sum(1 for department in departments if department["is_active"]),
            inactive_department_count=sum(1 for department in departments if not department["is_active"]),
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
        target_lookup_value: str = "",
    ) -> dict[str, object]:
        target_user = self.permission_service.find_user_for_role_assignment(user_id)
        roles = self._decorate_roles(self.list_roles_payload()["items"])
        assignable_roles = [role for role in roles if role["is_active"]]
        if selected_role_ids is None and target_user is not None:
            selected_role_ids = sorted(user_role.role_id for user_role in target_user.user_roles)
        selected_role_ids = sorted(set(selected_role_ids or []))

        current_roles: list[dict[str, object]] = []
        if target_user is not None:
            current_roles = [
                {
                    "id": user_role.role.id,
                    "name": user_role.role.name,
                    "code": user_role.role.code,
                    "description": user_role.role.description or "未填写角色说明",
                    "is_active": user_role.role.is_active,
                    "status_label": "启用中" if user_role.role.is_active else "已停用",
                }
                for user_role in sorted(target_user.user_roles, key=lambda item: item.role_id)
                if user_role.role is not None
            ]

        target_user_summary = self._build_target_user_summary(target_user, user_id)

        return self.build_base_context(
            request,
            current_admin,
            page_title="用户角色分配",
            page_key="identity.user_roles",
            page_intro="先确认当前正在调整的用户，再整体替换其角色集合；提交后立即按服务端权限规则生效。",
            error_message=error_message,
            success_message=success_message,
            target_user_id=user_id,
            target_user=target_user_summary,
            target_user_exists=target_user is not None,
            roles=roles,
            assignable_roles=assignable_roles,
            current_roles=current_roles,
            current_role_count=len(current_roles),
            selected_role_ids=selected_role_ids,
            target_lookup_value=target_lookup_value or str(target_user_summary["login_value"]),
        )

    def get_user_create_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
        created_user: UserCreateResult | None = None,
    ) -> dict[str, object]:
        departments = self.list_department_options()
        normalized_form = self._normalize_user_create_form(create_form or {})
        can_manage_roles = any(
            permission.code == IDENTITY_USERS_ROLES_WRITE
            for permission in self.permission_service.get_user_permissions(current_admin.id)
        )
        return self.build_base_context(
            request,
            current_admin,
            page_title="创建用户账号",
            page_key="identity.users.create",
            page_intro="按账号类型填写必要信息，创建完成后再继续处理角色分配等后续动作。",
            error_message=error_message,
            success_message=success_message,
            create_form=normalized_form,
            departments=departments,
            created_user=self._build_created_user_summary(created_user, can_manage_roles=can_manage_roles),
        )

    def list_rooms_payload(self) -> dict[str, object]:
        return self.room_service.list_admin_rooms()

    def list_department_options(self) -> list[dict[str, object]]:
        return [
            DepartmentRead.model_validate(department).model_dump()
            for department in self.department_service.list_active_departments()
        ]

    def get_rooms_context(
        self,
        request: Request,
        current_admin: User,
        *,
        error_message: str | None = None,
        success_message: str | None = None,
        create_form: dict[str, object] | None = None,
    ) -> dict[str, object]:
        departments = self.list_department_options()
        rooms = self._decorate_rooms(self.list_rooms_payload()["items"], departments)
        create_form = self._normalize_room_form(
            create_form
            or {
                "name": "",
                "location": "",
                "access_scope": "public",
                "department_id": "",
                "is_active": True,
                "open_time": "08:00",
                "close_time": "22:00",
            }
        )
        return self.build_base_context(
            request,
            current_admin,
            page_title="自习室管理",
            page_key="resource.rooms",
            page_intro="优先管理开放范围、院系可见性、开放时间和启用状态，避免高风险手填。",
            error_message=error_message,
            success_message=success_message,
            rooms=rooms,
            departments=departments,
            create_form=create_form,
            room_count=len(rooms),
            active_room_count=sum(1 for room in rooms if room["is_active"]),
            department_only_room_count=sum(1 for room in rooms if room["is_department_only"]),
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
        rooms = self._decorate_rooms(self.list_rooms_payload()["items"], self.list_department_options())
        seats = self._decorate_seats(self.list_seats_payload(room_id=room_id)["items"], rooms)
        create_form = self._normalize_seat_form(
            create_form
            or {
                "room_id": str(room_id or ""),
                "seat_code": "",
                "seat_label": "",
                "is_active": True,
                "is_window_side": False,
                "has_power_socket": False,
                "has_track_socket": False,
            }
        )
        selected_room = next((room for room in rooms if room["id"] == room_id), None)
        return self.build_base_context(
            request,
            current_admin,
            page_title="座位管理",
            page_key="resource.seats",
            page_intro="先按自习室聚焦，再维护座位编号、标签和属性，减少误操作。",
            error_message=error_message,
            success_message=success_message,
            seats=seats,
            rooms=rooms,
            selected_room_id=room_id,
            selected_room_label=selected_room["name"] if selected_room else "全部自习室",
            create_form=create_form,
            seat_count=len(seats),
            active_seat_count=sum(1 for seat in seats if seat["is_active"]),
            window_seat_count=sum(1 for seat in seats if seat["is_window_side"]),
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
            page_intro="查看当前配置值并提交更新，参数含义仍以服务端规则为准。",
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
            page_intro="页面只收集必要信息并调用公开预约服务，不在页面侧重复业务规则。",
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

    def list_reservation_records_payload(self, filters: AdminReservationQueryFilters) -> dict[str, object]:
        result = self.reservation_query_service.list_admin_records(filters)
        return {
            "items": [item.model_dump() for item in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    def get_reservation_records_context(
        self,
        request: Request,
        current_admin: User,
        *,
        user_id: int | None = None,
        student_no: str | None = None,
        room_id: int | None = None,
        seat_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        filters = AdminReservationQueryFilters(
            user_id=user_id,
            room_id=room_id,
            seat_id=seat_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        payload = self.list_reservation_records_payload(filters)
        return self.build_base_context(
            request,
            current_admin,
            page_title="预约记录查询",
            page_key="reservation.records",
            page_intro="按用户、房间、座位、状态和日期范围筛选预约记录，查询结果直接复用公开预约查询服务。",
            error_message=error_message,
            success_message=success_message,
            reservations=payload["items"],
            total=payload["total"],
            filters=filters.model_dump(),
        )

    def get_checkins_context(
        self,
        request: Request,
        current_admin: User,
        *,
        room_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        resolved_date_from = date_from or date.today()
        resolved_date_to = date_to or resolved_date_from
        rooms = self.admin_checkin_service.list_active_rooms()
        current_code = None
        if room_id is not None:
            code = self.admin_checkin_service.get_current_dynamic_code(room_id)
            current_code = {
                "room_id": code.room_id,
                "code": code.code,
                "time_slice_start": code.time_slice_start,
                "expires_at": code.expires_at,
                "remaining_seconds": code.remaining_seconds,
            }
        records = self.admin_checkin_service.list_records(
            room_id=room_id,
            date_from=resolved_date_from,
            date_to=resolved_date_to,
            page=page,
            page_size=page_size,
        )
        return self.build_base_context(
            request,
            current_admin,
            page_title="动态签到码",
            page_key="checkin.records",
            page_intro="查看指定自习室当前 5 分钟动态签到码状态、有效至时间和学生签到记录。",
            error_message=error_message,
            success_message=success_message,
            rooms=rooms,
            selected_room_id=room_id,
            date_from=resolved_date_from,
            date_to=resolved_date_to,
            page=page,
            page_size=page_size,
            current_code=current_code,
            checkin_records=records.items,
            checkin_total=records.total,
        )

    def get_notifications_context(
        self,
        request: Request,
        current_admin: User,
        *,
        reservation_id: int | None = None,
        notification_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        error_message: str | None = None,
        success_message: str | None = None,
        trigger_result: dict[str, object] | None = None,
    ) -> dict[str, object]:
        logs = self.admin_notification_service.list_logs(
            reservation_id=reservation_id,
            notification_type=notification_type,
            status=status,
            page=page,
            page_size=page_size,
        )
        return self.build_base_context(
            request,
            current_admin,
            page_title="通知日志",
            page_key="notification.logs",
            page_intro="查看通知发送记录，并按手动验收时间线触发已有内部通知任务。",
            error_message=error_message,
            success_message=success_message,
            notification_default_channel=self.admin_notification_service.settings.notification_default_channel,
            smtp_host=self.admin_notification_service.settings.smtp_host or "",
            logs=logs.items,
            total=logs.total,
            filters={
                "reservation_id": reservation_id,
                "notification_type": notification_type,
                "status": status,
                "page": page,
                "page_size": page_size,
            },
            trigger_result=trigger_result,
        )

    def get_statistics_context(
        self,
        request: Request,
        current_admin: User,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        error_message: str | None = None,
        success_message: str | None = None,
    ) -> dict[str, object]:
        resolved_date_from = date_from or date.today()
        resolved_date_to = date_to or resolved_date_from
        filters = StatisticsQueryFilters(date_from=resolved_date_from, date_to=resolved_date_to)
        payload = self.statistics_service.get_usage_statistics(filters).model_dump()
        return self.build_base_context(
            request,
            current_admin,
            page_title="统计查询",
            page_key="statistics.usage",
            page_intro="查看使用率与违约率统计结果，页面查询条件与既有统计接口保持一致。",
            error_message=error_message,
            success_message=success_message,
            overview=payload["overview"],
            rooms=payload["rooms"],
            seats=payload["seats"],
            filters={
                "date_from": resolved_date_from,
                "date_to": resolved_date_to,
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
        student_no: str | None = None,
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
            student_no=student_no,
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
            page_intro="按用户、学号、自习室和日期范围查询违约记录，所有筛选条件均可单独使用。",
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

    def _decorate_permissions(self, permissions: list[dict[str, object]]) -> list[dict[str, object]]:
        decorated: list[dict[str, object]] = []
        for permission in permissions:
            code = str(permission["code"])
            ui_copy = _PERMISSION_UI_COPY.get(code, {})
            decorated.append(
                {
                    **permission,
                    "display_name": ui_copy.get("name", permission["name"]),
                    "display_description": ui_copy.get(
                        "description",
                        permission.get("description") or "未填写权限说明。",
                    ),
                }
            )
        return decorated

    def _decorate_roles(self, roles: list[dict[str, object]]) -> list[dict[str, object]]:
        decorated: list[dict[str, object]] = []
        for role in roles:
            permissions = self._decorate_permissions(list(role.get("permissions", [])))
            decorated.append(
                {
                    **role,
                    "description": role.get("description") or "未填写角色说明。",
                    "status_label": "启用中" if role["is_active"] else "已停用",
                    "permission_count": len(permissions),
                    "permission_ids": [int(permission["id"]) for permission in permissions],
                    "permissions": permissions,
                    "permission_display_names": [str(permission["display_name"]) for permission in permissions],
                    "permission_codes": [str(permission["code"]) for permission in permissions],
                }
            )
        return decorated

    def _decorate_departments(self, departments: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                **department,
                "status_label": "启用中" if department["is_active"] else "已停用",
                "action": "deactivate" if department["is_active"] else "activate",
                "action_label": "停用院系" if department["is_active"] else "启用院系",
                "action_button_class": "danger" if department["is_active"] else "secondary",
            }
            for department in departments
        ]

    def _build_target_user_summary(self, user: User | None, user_id: int) -> dict[str, object]:
        if user is None:
            return {
                "id": user_id,
                "name": "未找到该用户",
                "status_label": "无法分配",
                "login_label": "当前目标",
                "login_value": str(user_id),
                "notification_email": "-",
                "show_notification_email": False,
                "department_name": "未知",
                "role_count": 0,
                "is_active": False,
                "exists": False,
            }

        notification_email = None
        if user.student_no:
            login_label = "学号"
            login_value = user.student_no
            notification_email = user.email
        elif user.email:
            login_label = "登录标识"
            login_value = user.email
        else:
            login_label = "用户 ID"
            login_value = str(user.id)

        return {
            "id": user.id,
            "name": user.name,
            "status_label": "启用中" if user.is_active else "已停用",
            "login_label": login_label,
            "login_value": login_value,
            "notification_email": notification_email or "-",
            "show_notification_email": notification_email is not None,
            "department_name": user.department.name if user.department is not None else "未绑定院系",
            "role_count": len(user.user_roles),
            "is_active": user.is_active,
            "exists": True,
        }

    def _decorate_rooms(
        self,
        rooms: list[dict[str, object]],
        departments: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        departments_by_id = {int(department["id"]): department for department in departments}
        decorated: list[dict[str, object]] = []
        for room in rooms:
            department_id = room.get("department_id")
            department = departments_by_id.get(int(department_id)) if department_id is not None else None
            is_department_only = bool(room["is_department_only"])
            decorated.append(
                {
                    **room,
                    "scope_label": "院系专属" if is_department_only else "公共开放",
                    "status_label": "启用中" if room["is_active"] else "已停用",
                    "department_label": (
                        str(department["name"])
                        if is_department_only and department is not None
                        else (
                            f"院系 ID {department_id}"
                            if is_department_only and department_id is not None
                            else "不限院系"
                        )
                    ),
                    "open_time_text": self._format_time_value(room["open_time"]),
                    "close_time_text": self._format_time_value(room["close_time"]),
                    "access_scope": "department" if is_department_only else "public",
                }
            )
        return decorated

    def _decorate_seats(
        self,
        seats: list[dict[str, object]],
        rooms: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        rooms_by_id = {int(room["id"]): room for room in rooms}
        decorated: list[dict[str, object]] = []
        for seat in seats:
            room = rooms_by_id.get(int(seat["room_id"]))
            attribute_labels = []
            if seat["is_window_side"]:
                attribute_labels.append("靠窗")
            if seat["has_power_socket"]:
                attribute_labels.append("固定插座")
            if seat["has_track_socket"]:
                attribute_labels.append("移动导轨插座")
            decorated.append(
                {
                    **seat,
                    "room_name": room["name"] if room else f"自习室 {seat['room_id']}",
                    "room_location": room["location"] if room else "",
                    "status_label": "启用中" if seat["is_active"] else "已停用",
                    "attribute_labels": attribute_labels or ["常规座位"],
                }
            )
        return decorated

    def _normalize_role_form(self, role_form: dict[str, object]) -> dict[str, object]:
        permission_ids: list[int] = []
        for value in role_form.get("permission_ids", []):
            text = str(value).strip()
            if text.isdigit():
                permission_ids.append(int(text))

        return {
            "role_id": "" if role_form.get("role_id") is None else str(role_form.get("role_id", "")),
            "name": str(role_form.get("name", "")),
            "code": str(role_form.get("code", "")),
            "description": str(role_form.get("description", "")),
            "is_active": bool(role_form.get("is_active", True)),
            "permission_ids": sorted(set(permission_ids)),
        }

    def _normalize_department_form(self, create_form: dict[str, object]) -> dict[str, object]:
        return {
            "name": str(create_form.get("name", "")),
            "code": str(create_form.get("code", "")),
            "is_active": bool(create_form.get("is_active", True)),
        }

    def _normalize_room_form(self, create_form: dict[str, object]) -> dict[str, object]:
        access_scope = str(create_form.get("access_scope") or "").strip() or (
            "department" if create_form.get("department_id") else "public"
        )
        if access_scope not in {"public", "department"}:
            access_scope = "public"
        return {
            "name": str(create_form.get("name", "")),
            "location": str(create_form.get("location", "")),
            "access_scope": access_scope,
            "department_id": "" if create_form.get("department_id") is None else str(create_form.get("department_id", "")),
            "is_active": bool(create_form.get("is_active", True)),
            "open_time": self._format_time_value(create_form.get("open_time") or "08:00"),
            "close_time": self._format_time_value(create_form.get("close_time") or "22:00"),
        }

    def _normalize_seat_form(self, create_form: dict[str, object]) -> dict[str, object]:
        return {
            "room_id": "" if create_form.get("room_id") is None else str(create_form.get("room_id", "")),
            "seat_code": str(create_form.get("seat_code", "")),
            "seat_label": str(create_form.get("seat_label", "")),
            "is_active": bool(create_form.get("is_active", True)),
            "is_window_side": bool(create_form.get("is_window_side", False)),
            "has_power_socket": bool(create_form.get("has_power_socket", False)),
            "has_track_socket": bool(create_form.get("has_track_socket", False)),
        }

    def _normalize_user_create_form(self, create_form: dict[str, object]) -> dict[str, object]:
        account_type = str(create_form.get("account_type") or "student").strip().lower()
        if account_type not in {"student", "admin"}:
            account_type = "student"
        return {
            "account_type": account_type,
            "name": str(create_form.get("name", "")),
            "student_no": str(create_form.get("student_no", "")),
            "email": str(create_form.get("email", "")),
            "notification_email": str(create_form.get("notification_email", "")),
            "password": "",
            "department_id": "" if create_form.get("department_id") is None else str(create_form.get("department_id", "")),
            "is_active": bool(create_form.get("is_active", True)),
        }

    def _build_created_user_summary(
        self,
        created_user: UserCreateResult | None,
        *,
        can_manage_roles: bool,
    ) -> dict[str, object] | None:
        if created_user is None:
            return None
        needs_role_assignment = created_user.account_type == "admin"
        login_label = "学号" if created_user.account_type == "student" else "登录标识"
        login_value = created_user.student_no if created_user.account_type == "student" else created_user.email
        notification_email = created_user.notification_email if created_user.account_type == "student" else None
        return {
            "id": created_user.id,
            "name": created_user.name,
            "account_type": created_user.account_type,
            "account_type_label": "学生账号" if created_user.account_type == "student" else "管理员账号",
            "login_label": login_label,
            "login_value": login_value or "-",
            "notification_email": notification_email or "-",
            "show_notification_email": created_user.account_type == "student",
            "department_name": created_user.department.name if created_user.department is not None else "未绑定院系",
            "status_label": "启用中" if created_user.is_active else "已停用",
            "role_assignment_href": (
                f"/admin/users/{created_user.id}/roles" if needs_role_assignment and can_manage_roles else ""
            ),
            "show_role_assignment_hint": needs_role_assignment and can_manage_roles,
            "next_step_message": (
                "创建完成后，请继续分配管理员角色。"
                if needs_role_assignment and can_manage_roles
                else (
                    "创建完成后，请让拥有角色分配权限的管理员继续配置角色。"
                    if needs_role_assignment
                    else "学生账号已完成创建，可直接交付登录。"
                )
            ),
        }

    def _format_time_value(self, value: object) -> str:
        if isinstance(value, time_value):
            return value.strftime("%H:%M")
        text = str(value or "").strip()
        if len(text) >= 5 and text[2] == ":":
            return text[:5]
        return text
