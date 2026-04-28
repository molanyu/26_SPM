from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        details: object | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.status_code = status_code or self.status_code
        self.code = code or self.code


class BadRequestError(AppError):
    code = "bad_request"
    status_code = 400


class AuthenticationError(AppError):
    code = "unauthenticated"
    status_code = 401


class AuthorizationError(AppError):
    code = "forbidden"
    status_code = 403


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ConflictError(AppError):
    code = "conflict"
    status_code = 409

