from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.constants import IDENTITY_PERMISSIONS_READ, IDENTITY_ROLES_WRITE
from app.modules.identity.dependencies import require_admin_permission
from app.modules.system_config.models.system_config import SystemConfig
from app.modules.system_config.schemas.config import SystemConfigRead, SystemConfigUpdateRequest
from app.modules.system_config.services.config_service import ConfigService

router = APIRouter(prefix="/admin", tags=["system-config"])


def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    return ConfigService(db)


def _build_config_read(config_service: ConfigService, config: SystemConfig) -> SystemConfigRead:
    return SystemConfigRead(
        id=config.id,
        config_key=config.config_key,
        config_value=config_service.parse_config_value(config),
        value_type=config.value_type,
        description=config.description,
        updated_at=config.updated_at,
    )


@router.get(
    "/system-configs",
    dependencies=[Depends(require_admin_permission(IDENTITY_PERMISSIONS_READ))],
)
def list_system_configs(config_service: ConfigService = Depends(get_config_service)):
    items = [_build_config_read(config_service, config).model_dump() for config in config_service.list_configs()]
    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "page_size": len(items),
    }


@router.put(
    "/system-configs/{config_key}",
    dependencies=[Depends(require_admin_permission(IDENTITY_ROLES_WRITE))],
)
def update_system_config(
    config_key: str,
    payload: SystemConfigUpdateRequest,
    config_service: ConfigService = Depends(get_config_service),
):
    config = config_service.update_config(config_key, payload.config_value)
    return {
        "success": True,
        "message": "System config updated successfully.",
        "data": _build_config_read(config_service, config).model_dump(),
    }
