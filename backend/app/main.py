import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.router import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import (
    configure_logging,
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)
from backend.app.core.rate_limit import enforce_public_rate_limit
from backend.app.infrastructure.database.session import DatabaseManager, get_db_session

logger = logging.getLogger(__name__)

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_NO_STORE_PREFIXES = ("/auth", "/saved-lists")


def _sanitize_request_id(raw_value: str | None) -> str:
    if raw_value and _REQUEST_ID_RE.match(raw_value):
        return raw_value
    return uuid.uuid4().hex


def _extract_trace_id(header_value: str | None) -> str:
    if not header_value:
        return ""
    trace_part = header_value.split("/", 1)[0].strip()
    if _REQUEST_ID_RE.match(trace_part):
        return trace_part
    return ""


def create_app(
    *,
    settings: Settings | None = None,
    database_url_override: str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application with lifespan-managed async DB."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        db_manager = DatabaseManager()
        db_manager.init(resolved_settings, url_override=database_url_override)
        application.state.settings = resolved_settings
        application.state.db_manager = db_manager
        try:
            yield
        finally:
            await db_manager.dispose()

    docs_enabled = resolved_settings.ENVIRONMENT != "production"
    application = FastAPI(
        title="CoRe - MHT-CET College Predictor",
        debug=False,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context_and_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _sanitize_request_id(request.headers.get("X-Request-ID"))
        trace_id = _extract_trace_id(request.headers.get("X-Cloud-Trace-Context"))
        req_token = set_request_id(request_id)
        trace_token = set_trace_id(trace_id)
        started_at = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            reset_trace_id(trace_token)
            reset_request_id(req_token)

        duration_ms = round((time.monotonic() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith(_NO_STORE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"

        logger.info(
            "method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/")
    async def home() -> dict[str, str]:
        return {"message": "MHT-CET College Predictor"}

    @application.api_route(
        "/ping",
        methods=["GET", "HEAD"],
        dependencies=[Depends(enforce_public_rate_limit)],
    )
    async def ping(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @application.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/health/ready")
    async def readiness(session: AsyncSession = Depends(get_db_session)) -> Response:
        try:
            await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unavailable"},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})

    return application
