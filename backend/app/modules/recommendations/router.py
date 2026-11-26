from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings, get_app_settings
from backend.app.core.rate_limit import enforce_public_rate_limit
from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.recommendations.schemas import (
    RecommenderQuery,
    RecommenderResponse,
)
from backend.app.modules.recommendations.service import RecommendationsService

router = APIRouter(prefix="/recommender", tags=["Recommender"])
_recommendations_service = RecommendationsService()


@router.get(
    "/",
    response_model=RecommenderResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
async def recommend_colleges(
    response: Response,
    filters: Annotated[RecommenderQuery, Query()],
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> RecommenderResponse:
    response.headers["Cache-Control"] = "public, max-age=3600"
    return await _recommendations_service.get_recommendations(
        session,
        filters,
        settings=settings,
    )
