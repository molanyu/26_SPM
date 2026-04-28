from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.system_config.models.system_config import SystemConfig


class ConfigRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_keys(self, config_keys: list[str]) -> list[SystemConfig]:
        statement = (
            select(SystemConfig)
            .where(SystemConfig.config_key.in_(config_keys))
            .order_by(SystemConfig.config_key.asc())
        )
        return list(self.session.scalars(statement))

    def get_by_key(self, config_key: str) -> SystemConfig | None:
        statement = select(SystemConfig).where(SystemConfig.config_key == config_key)
        return self.session.scalar(statement)

    def create_many(self, configs: list[SystemConfig]) -> list[SystemConfig]:
        self.session.add_all(configs)
        self.session.commit()
        return configs

    def save(self, config: SystemConfig) -> SystemConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config
