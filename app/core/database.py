from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False, future=True)
_configured_database_url: str | None = None


def _build_engine(database_url: str) -> Engine:
    kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def configure_database(database_url: str) -> None:
    global engine, _configured_database_url
    if engine is not None and _configured_database_url == database_url:
        return
    if engine is not None:
        engine.dispose()
    engine = _build_engine(database_url)
    SessionLocal.configure(bind=engine)
    _configured_database_url = database_url


def init_database() -> None:
    if engine is None:
        raise RuntimeError("Database is not configured.")
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("Database is not configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

