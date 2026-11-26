from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.trends.repository import TrendsRepository
from backend.app.modules.trends.schemas import TrendsQuery, TrendsResponse


class TrendsService:
    """Business logic for historical cutoff trends."""

    def __init__(self, repository: TrendsRepository | None = None) -> None:
        self._repository = repository or TrendsRepository()

    async def get_trends(
        self,
        session: AsyncSession,
        trend_query: TrendsQuery,
    ) -> TrendsResponse:
        category = "GOPENS" if trend_query.category == "All" else trend_query.category
        trend_points = await self._repository.get_branch_trends(
            session,
            branch_code=trend_query.branch_code,
            category=category,
            level=trend_query.level,
        )
        return TrendsResponse(
            branch_code=trend_query.branch_code,
            count=len(trend_points),
            trends=trend_points,
        )
