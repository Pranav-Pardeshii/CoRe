import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.logging import get_request_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class ConflictError(AppError):
    """Raised when an operation conflicts with existing state or uniqueness constraints."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist or is not owned by the caller."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppError):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Invalid credentials") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that prevent internal error disclosure."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "Database error type=%s request_id=%s",
            exc.__class__.__name__,
            get_request_id(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred."},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled error type=%s request_id=%s",
            exc.__class__.__name__,
            get_request_id(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )
