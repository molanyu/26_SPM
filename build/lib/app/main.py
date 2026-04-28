from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.admin_portal.routes.router import router as admin_portal_router
from app.core.config import Settings, load_settings
from app.core.database import SessionLocal, configure_database, init_database
from app.core.errors import AppError
from app.core.model_registry import import_all_models
from app.modules.assistant.api.router import router as assistant_router
from app.modules.checkin.api.router import router as checkin_router
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.services.auth_service import AdminSessionStore
from app.modules.identity.services.bootstrap_service import BootstrapService
from app.modules.reservation.api.router import router as reservation_router
from app.modules.resource.api.router import router as resource_router
from app.modules.system_config.api.router import router as system_config_router
from app.modules.violation.api.router import router as violation_router


def _error_payload(code: str, message: str, details: object | None = None) -> dict[str, object | None]:
    return {
        "code": code,
        "message": message,
        "details": details,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    import_all_models()
    configure_database(settings.database_url)

    def run_identity_bootstrap() -> None:
        if not settings.identity_bootstrap_enabled:
            return
        if not settings.identity_bootstrap_admin_email or not settings.identity_bootstrap_admin_password:
            raise RuntimeError(
                "IDENTITY_BOOTSTRAP_ADMIN_EMAIL and IDENTITY_BOOTSTRAP_ADMIN_PASSWORD are required when bootstrap is enabled.",
            )
        with SessionLocal() as session:
            BootstrapService(session).bootstrap(
                admin_email=settings.identity_bootstrap_admin_email,
                admin_name=settings.identity_bootstrap_admin_name,
                admin_password=settings.identity_bootstrap_admin_password,
            )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.database_auto_create:
            init_database()
        run_identity_bootstrap()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.admin_session_store = AdminSessionStore(settings.admin_session_ttl_minutes)
    app.include_router(admin_portal_router)
    app.include_router(identity_router)
    app.include_router(resource_router)
    app.include_router(system_config_router)
    app.include_router(reservation_router)
    app.include_router(checkin_router)
    app.include_router(violation_router)
    app.include_router(assistant_router)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            payload = {
                "code": exc.detail.get("code", "http_error"),
                "message": exc.detail.get("message", "Request failed."),
                "details": exc.detail.get("details"),
            }
        else:
            payload = _error_payload("http_error", str(exc.detail), None)
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload("validation_error", "Request validation failed.", exc.errors()),
        )

    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
