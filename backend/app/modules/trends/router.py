from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.trends.schemas import TrendsQuery, TrendsResponse
from backend.app.modules.trends.service import TrendsService

router = APIRouter(prefix="/trends", tags=["Trends"])
_trends_service = TrendsService()


@router.get("/", response_model=TrendsResponse)
async def get_trends(
    trend_query: Annotated[TrendsQuery, Query()],
    session: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    return await _trends_service.get_trends(session, trend_query)
