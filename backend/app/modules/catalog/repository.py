from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.catalog.models import Branch, College


@dataclass(frozen=True)
class BranchCollegeInfo:
    """Public branch and college metadata returned by the catalog module."""

    college_code: str
    college_name: str
    branch_name: str


class CatalogRepository:
    """Read-only catalog lookups across colleges and branches."""

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
