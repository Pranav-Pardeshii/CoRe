import logging
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
from backend.app.core.logging import configure_logging, set_request_id
from backend.app.infrastructure.database.session import DatabaseManager, get_db_session

logger = logging.getLogger(__name__)


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

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        set_request_id(request_id)
        started_at = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
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

    @application.api_route("/ping", methods=["GET", "HEAD"])
    async def ping(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "Aiven MySQL Database is awake!"}

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


app = create_app()
