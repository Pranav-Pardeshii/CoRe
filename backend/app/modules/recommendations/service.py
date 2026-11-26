from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.modules.recommendations.repository import RecommendationsRepository
from backend.app.modules.recommendations.schemas import (
    RecommenderQuery,
    RecommenderResponse,
)


class RecommendationsService:
    """Business logic for filtering and paginating college recommendations."""

    def __init__(self, repository: RecommendationsRepository | None = None) -> None:
        self._repository = repository or RecommendationsRepository()

    async def get_recommendations(
        self,
        session: AsyncSession,
        filters: RecommenderQuery,
        *,
        settings: Settings | None = None,
    ) -> RecommenderResponse:
        division = None if filters.division == "All" else filters.division
        branch = None if filters.branch == "All" else filters.branch
        category = None if filters.category == "All" else filters.category
        limit = filters.page_size
        offset = (filters.page - 1) * limit
        years = settings.RECOMMENDER_YEARS if settings is not None else None

        college_records, total_count = await self._repository.find_eligible_colleges(
            session,
            percentile=filters.percentile,
            category=category,
            branch=branch,
            division=division,
            limit=limit,
            offset=offset,
            years=years,
        )
        return RecommenderResponse(eligible_colleges=college_records, count=total_count)
