from sqlalchemy import case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.auth.models import User
from backend.app.modules.saved_lists.models import SavedListItem
from backend.app.modules.saved_lists.schemas import SavedListItemOut


class SavedListRepository:
    """SQLAlchemy persistence operations for user saved lists."""

    async def lock_user_for_update(self, session: AsyncSession, user_id: int) -> bool:
        """Lock the parent user row to serialize list mutations and verify existence."""
        stmt = select(User.id).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_count_and_max_sort_order(
        self, session: AsyncSession, user_id: int
    ) -> tuple[int, int | None]:
        """Return (item_count, max_sort_order) for the user's saved list."""
        stmt = select(
            func.count(SavedListItem.id),
            func.max(SavedListItem.sort_order),
        ).where(SavedListItem.user_id == user_id)
        row = (await session.execute(stmt)).one()
        return int(row[0] or 0), row[1]

    async def create_item(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        college_code: str,
        branch_code: str,
        college_name: str,
        branch_name: str,
        sort_order: int,
    ) -> SavedListItem:
        saved_item = SavedListItem(
            user_id=user_id,
            college_code=college_code,
            branch_code=branch_code,
            college_name=college_name,
            branch_name=branch_name,
            sort_order=sort_order,
        )
        session.add(saved_item)
        await session.flush()
        return saved_item

    async def delete_item(self, session: AsyncSession, *, item_id: int, user_id: int) -> int:
        stmt = delete(SavedListItem).where(
            SavedListItem.id == item_id,
            SavedListItem.user_id == user_id,
        )
        delete_result = await session.execute(stmt)
        return int(delete_result.rowcount or 0)  # type: ignore[attr-defined]

    async def get_owned_ids_for_update(self, session: AsyncSession, user_id: int) -> set[int]:
        stmt = select(SavedListItem.id).where(SavedListItem.user_id == user_id).with_for_update()
        query_result = await session.execute(stmt)
        return {int(row[0]) for row in query_result.all()}

    async def bulk_update_sort_orders(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        ordered_list: list[int],
    ) -> None:
        """Update all sort_order values in a single SQL UPDATE ... CASE statement."""
        if not ordered_list:
            return
        whens = {item_id: index + 1 for index, item_id in enumerate(ordered_list)}
        stmt = (
            update(SavedListItem)
            .where(
                SavedListItem.user_id == user_id,
                SavedListItem.id.in_(ordered_list),
            )
            .values(sort_order=case(whens, value=SavedListItem.id))
        )
        await session.execute(stmt)

    async def list_items(self, session: AsyncSession, user_id: int) -> list[SavedListItemOut]:
        stmt = (
            select(SavedListItem.id, SavedListItem.college_name, SavedListItem.branch_name)
            .where(SavedListItem.user_id == user_id)
            .order_by(SavedListItem.sort_order.asc())
        )
        query_result = await session.execute(stmt)
        return [
            SavedListItemOut(
                id=int(row[0]),
                college_name=row[1],
                branch_name=row[2],
            )
            for row in query_result.all()
        ]
