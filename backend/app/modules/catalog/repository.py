import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.catalog.models import AdmissionCutoff, Branch, College
from backend.app.modules.catalog.schemas import CatalogFiltersResponse

_FILTERS_CACHE_TTL_SECONDS = 600.0
_filters_cache: tuple[float, CatalogFiltersResponse] | None = None


def clear_catalog_cache() -> None:
    """Clear the cached catalog filter options (primarily for test isolation)."""
    global _filters_cache
    _filters_cache = None


@dataclass(frozen=True)
class BranchCollegeInfo:
    """Public branch and college metadata returned by the catalog module."""

    college_code: str
    college_name: str
    branch_name: str


class CatalogRepository:
    """Read-only catalog lookups across colleges, branches, and cutoff metadata."""

    async def get_branch_with_college(
        self,
        session: AsyncSession,
        branch_code: str,
    ) -> BranchCollegeInfo | None:
        stmt = (
            select(College.college_code, College.college_name, Branch.branch_name)
            .join(Branch, Branch.college_code == College.college_code)
            .where(Branch.branch_code == branch_code)
        )
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return BranchCollegeInfo(
            college_code=row[0],
            college_name=row[1],
            branch_name=row[2],
        )

    async def get_filter_options(self, session: AsyncSession) -> CatalogFiltersResponse:
        """Fetch sorted distinct filter options from MySQL with an in-process 600s TTL cache."""
        global _filters_cache
        now = time.monotonic()
        if _filters_cache is not None and (now - _filters_cache[0]) < _FILTERS_CACHE_TTL_SECONDS:
            return _filters_cache[1]

        categories_res = await session.execute(
            select(AdmissionCutoff.category).distinct().order_by(AdmissionCutoff.category.asc())
        )
        branches_res = await session.execute(
            select(Branch.branch_name).distinct().order_by(Branch.branch_name.asc())
        )
        divisions_res = await session.execute(
            select(College.division)
            .where(College.division.is_not(None), College.division != "")
            .distinct()
            .order_by(College.division.asc())
        )
        years_res = await session.execute(
            select(AdmissionCutoff.admission_year)
            .distinct()
            .order_by(AdmissionCutoff.admission_year.desc())
        )
        levels_res = await session.execute(
            select(AdmissionCutoff.level).distinct().order_by(AdmissionCutoff.level.asc())
        )

        response = CatalogFiltersResponse(
            categories=[str(row[0]) for row in categories_res.all()],
            branches=[str(row[0]) for row in branches_res.all()],
            divisions=[str(row[0]) for row in divisions_res.all() if row[0] is not None],
            years=[int(row[0]) for row in years_res.all()],
            levels=[str(row[0]) for row in levels_res.all()],
        )
        _filters_cache = (now, response)
        return response
