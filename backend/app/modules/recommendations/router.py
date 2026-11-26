from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.recommendations.schemas import (
    RecommenderQuery,
    RecommenderResponse,
)
from backend.app.modules.recommendations.service import RecommendationsService

router = APIRouter(prefix="/recommender", tags=["Recommender"])
_recommendations_service = RecommendationsService()


@router.get("/", response_model=RecommenderResponse)
async def recommend_colleges(
    filters: Annotated[RecommenderQuery, Query()],
    session: AsyncSession = Depends(get_db_session),
) -> RecommenderResponse:
    return await _recommendations_service.get_recommendations(session, filters)
