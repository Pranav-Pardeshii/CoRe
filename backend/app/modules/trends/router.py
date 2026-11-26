from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rate_limit import enforce_public_rate_limit
from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.trends.schemas import TrendsQuery, TrendsResponse
from backend.app.modules.trends.service import TrendsService

router = APIRouter(prefix="/trends", tags=["Trends"])
_trends_service = TrendsService()


@router.get(
    "/",
    response_model=TrendsResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
async def get_trends(
    response: Response,
    trend_query: Annotated[TrendsQuery, Query()],
    session: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    response.headers["Cache-Control"] = "public, max-age=3600"
    return await _trends_service.get_trends(session, trend_query)
