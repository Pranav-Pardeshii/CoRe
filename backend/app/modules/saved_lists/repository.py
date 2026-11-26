from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.saved_lists.models import SavedListItem
from backend.app.modules.saved_lists.schemas import SavedListItemOut


class SavedListRepository:
    """SQLAlchemy persistence operations for user saved lists."""

    async def get_max_sort_order_for_update(
        self, session: AsyncSession, user_id: int
    ) -> int | None:
        # Lock existing rows for this user in the active transaction to serialize order allocation.
        lock_stmt = (
            select(SavedListItem.sort_order)
            .where(SavedListItem.user_id == user_id)
            .with_for_update()
        )
        await session.execute(lock_stmt)
        max_stmt = select(func.max(SavedListItem.sort_order)).where(
            SavedListItem.user_id == user_id
        )
        query_result = await session.execute(max_stmt)
        return query_result.scalar_one()

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

    async def update_sort_order(
        self,
        session: AsyncSession,
        *,
        item_id: int,
        user_id: int,
        sort_order: int,
    ) -> None:
        stmt = (
            update(SavedListItem)
            .where(SavedListItem.id == item_id, SavedListItem.user_id == user_id)
            .values(sort_order=sort_order)
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
