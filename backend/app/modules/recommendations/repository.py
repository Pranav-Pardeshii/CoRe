from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.app.modules.catalog.models import AdmissionCutoff, Branch, College
from backend.app.modules.recommendations.schemas import EligibleCollegeOut


class RecommendationsRepository:
    """SQLAlchemy queries for MHT-CET college eligibility recommendations."""

    @staticmethod
    def _build_filtered_grouped_query(
        *,
        percentile: float,
        category: str | None,
        branch: str | None,
        division: str | None,
    ) -> Select[str, str, str, float, float]:
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
                AdmissionCutoff.admission_year.in_([2024, 2025]),
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
    ) -> tuple[list[EligibleCollegeOut], int]:
        base_stmt = self._build_filtered_grouped_query(
            percentile=percentile,
            category=category,
            branch=branch,
            division=division,
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await session.execute(count_stmt)
        total_count = int(count_result.scalar_one())

        if total_count == 0:
            return [], 0

        data_stmt = (
            base_stmt.order_by(func.max(AdmissionCutoff.percentile).desc())
            .limit(limit)
            .offset(offset)
        )
        query_result = await session.execute(data_stmt)
        college_records = [
            EligibleCollegeOut(
                college=row[0],
                branch=row[1],
                branch_code=row[2],
                min_cutoff=float(row[3]),
                max_cutoff=float(row[4]),
            )
            for row in query_result.all()
        ]
        return college_records, total_count
