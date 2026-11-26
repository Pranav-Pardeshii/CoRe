from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import enforce_auth_rate_limit
from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.auth.schemas import (
    RegisterResponse,
    TokenResponse,
    UserRegisterRequest,
)
from backend.app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
_auth_service = AuthService()


@router.post(
    "/register",
    response_model=RegisterResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def register(
    registration_request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    return await _auth_service.register(
        session,
        username=registration_request.username,
        password=registration_request.password,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    return await _auth_service.login(
        session,
        username=credentials.username,
        password=credentials.password,
        settings=settings,
    )
