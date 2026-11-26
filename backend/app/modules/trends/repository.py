from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.catalog.models import AdmissionCutoff
from backend.app.modules.trends.schemas import TrendPointOut


class TrendsRepository:
    """SQLAlchemy queries for historical cutoff trends."""

    async def get_branch_trends(
        self,
        session: AsyncSession,
        *,
        branch_code: str,
        category: str,
    ) -> list[TrendPointOut]:
        stmt = (
            select(
                AdmissionCutoff.admission_year,
                AdmissionCutoff.cap_round,
                AdmissionCutoff.percentile,
            )
            .where(
                AdmissionCutoff.branch_code == branch_code,
                AdmissionCutoff.category == category,
                AdmissionCutoff.admission_stage == "I",
            )
            .order_by(AdmissionCutoff.admission_year, AdmissionCutoff.cap_round)
        )
        query_result = await session.execute(stmt)
        return [
            TrendPointOut(
                year=int(row[0]),
                round=int(row[1]),
                percentile=float(row[2]),
            )
            for row in query_result.all()
        ]
