import time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.app.modules.catalog.models import AdmissionCutoff, Branch, College
from backend.app.modules.recommendations.schemas import EligibleCollegeOut

_YEARS_CACHE_TTL_SECONDS = 600.0
_years_cache: dict[int, tuple[float, list[int]]] = {}


def clear_recommendations_cache() -> None:
    """Clear the cached latest admission years (primarily for test isolation)."""
    _years_cache.clear()


class RecommendationsRepository:
    """SQLAlchemy queries for MHT-CET college eligibility recommendations."""

    async def get_latest_years(self, session: AsyncSession, limit: int = 2) -> list[int]:
        """Return the latest distinct admission years with an in-process 600s TTL cache."""
        now = time.monotonic()
        cached = _years_cache.get(limit)
        if cached is not None and (now - cached[0]) < _YEARS_CACHE_TTL_SECONDS:
            return list(cached[1])

        stmt = (
            select(AdmissionCutoff.admission_year)
            .distinct()
            .order_by(AdmissionCutoff.admission_year.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        years = [int(row[0]) for row in result.all()]
        if years:
            _years_cache[limit] = (now, years)
        return years

    @staticmethod
    def _build_filtered_grouped_query(
        *,
        years: list[int],
        percentile: float,
        category: str | None,
        branch: str | None,
        division: str | None,
    ) -> Select[str, str, str, Decimal, Decimal]:
        stmt = (
            select(
                College.college_name,
                Branch.branch_name,
                AdmissionCutoff.branch_code,
                func.min(AdmissionCutoff.percentile).label("min_cutoff"),
                func.max(AdmissionCutoff.percentile).label("max_cutoff"),
            )
            .join(Branch, AdmissionCutoff.branch_code == Branch.branch_code)
            .join(College, Branch.college_code == College.college_code)
            .where(
                AdmissionCutoff.admission_year.in_(years),
                AdmissionCutoff.admission_stage == "I",
            )
        )
        if branch is not None:
            stmt = stmt.where(Branch.branch_name == branch)
        if category is not None:
            stmt = stmt.where(AdmissionCutoff.category == category)
        if division is not None:
            stmt = stmt.where(College.division == division)

        return stmt.group_by(
            College.college_name,
            Branch.branch_name,
            AdmissionCutoff.branch_code,
        ).having(func.min(AdmissionCutoff.percentile) <= percentile)

    async def find_eligible_colleges(
        self,
        session: AsyncSession,
        *,
        percentile: float,
        category: str | None,
        branch: str | None,
        division: str | None,
        limit: int,
        offset: int,
        years: list[int] | None = None,
    ) -> tuple[list[EligibleCollegeOut], int]:
        target_years = years if years is not None else await self.get_latest_years(session, limit=2)
        if not target_years:
            return [], 0

        base_stmt = self._build_filtered_grouped_query(
            years=target_years,
            percentile=percentile,
            category=category,
            branch=branch,
            division=division,
        )
        windowed_stmt = (
            base_stmt.add_columns(func.count().over().label("total_count"))
            .order_by(
                func.max(AdmissionCutoff.percentile).desc(),
                AdmissionCutoff.branch_code.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        query_result = await session.execute(windowed_stmt)
        rows = query_result.all()

        if not rows:
            if offset == 0:
                return [], 0
            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            total_count = int((await session.execute(count_stmt)).scalar_one())
            return [], total_count

        total_count = int(rows[0][5])
        college_records = [
            EligibleCollegeOut(
                college=row[0],
                branch=row[1],
                branch_code=row[2],
                min_cutoff=float(row[3]),
                max_cutoff=float(row[4]),
            )
            for row in rows
        ]
        return college_records, total_count
