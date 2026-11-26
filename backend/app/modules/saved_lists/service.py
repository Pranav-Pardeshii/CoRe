from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from backend.app.modules.catalog.repository import CatalogRepository
from backend.app.modules.saved_lists.repository import SavedListRepository
from backend.app.modules.saved_lists.schemas import (
    SavedListMessageResponse,
    SavedListResponse,
)

MAX_SAVED_LIST_ITEMS = 100
_MYSQL_DUPLICATE_ENTRY_ERRNO = 1062


def _is_duplicate_entry_error(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", None)
    if args and args[0] == _MYSQL_DUPLICATE_ENTRY_ERRNO:
        return True
    return "duplicate" in str(exc).lower()


class SavedListService:
    """Business logic and transaction boundaries for user saved lists."""

    def __init__(
        self,
        repository: SavedListRepository | None = None,
        catalog_repository: CatalogRepository | None = None,
    ) -> None:
        self._repository = repository or SavedListRepository()
        self._catalog_repository = catalog_repository or CatalogRepository()

    async def create_item(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        branch_code: str,
    ) -> SavedListMessageResponse:
        branch_info = await self._catalog_repository.get_branch_with_college(session, branch_code)
        if branch_info is None:
            raise AppError("Invalid college_code or branch_code!", status_code=400)

        try:
            user_exists = await self._repository.lock_user_for_update(session, user_id)
            if not user_exists:
                await session.rollback()
                raise UnauthorizedError("User account not found.")

            item_count, max_sort_order = await self._repository.get_count_and_max_sort_order(
                session, user_id
            )
            if item_count >= MAX_SAVED_LIST_ITEMS:
                await session.rollback()
                raise AppError(
                    f"Saved list limit of {MAX_SAVED_LIST_ITEMS} items reached.",
                    status_code=400,
                )

            next_sort_order = 1 if max_sort_order is None else max_sort_order + 1
            await self._repository.create_item(
                session,
                user_id=user_id,
                college_code=branch_info.college_code,
                branch_code=branch_code,
                college_name=branch_info.college_name,
                branch_name=branch_info.branch_name,
                sort_order=next_sort_order,
            )
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if _is_duplicate_entry_error(exc):
                raise ConflictError("You already saved this Item") from exc
            raise AppError("Unable to save item due to data constraint.", status_code=400) from exc
        except AppError:
            raise
        except Exception:
            await session.rollback()
            raise

        return SavedListMessageResponse(message="Item saved successfully.")

    async def delete_item(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        item_id: int,
    ) -> SavedListMessageResponse:
        try:
            user_exists = await self._repository.lock_user_for_update(session, user_id)
            if not user_exists:
                await session.rollback()
                raise UnauthorizedError("User account not found.")

            deleted_count = await self._repository.delete_item(
                session,
                item_id=item_id,
                user_id=user_id,
            )
            if deleted_count == 0:
                await session.rollback()
                raise NotFoundError("Item not found!")
            await session.commit()
        except AppError:
            raise
        except Exception:
            await session.rollback()
            raise

        return SavedListMessageResponse(message="Item deleted successfully!")

    async def reorder(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        ordered_list: list[int],
    ) -> SavedListMessageResponse:
        if len(ordered_list) != len(set(ordered_list)):
            raise AppError("Invalid Input!", status_code=400)

        try:
            user_exists = await self._repository.lock_user_for_update(session, user_id)
            if not user_exists:
                await session.rollback()
                raise UnauthorizedError("User account not found.")

            owned_ids = await self._repository.get_owned_ids_for_update(session, user_id)
            if set(ordered_list) != owned_ids:
                await session.rollback()
                raise AppError("Invalid Input!", status_code=400)

            await self._repository.bulk_update_sort_orders(
                session,
                user_id=user_id,
                ordered_list=ordered_list,
            )
            await session.commit()
        except AppError:
            raise
        except Exception:
            await session.rollback()
            raise

        return SavedListMessageResponse(message="Bingo! list reordered successfully!")

    async def get_saved_list(
        self,
        session: AsyncSession,
        *,
        user_id: int,
    ) -> SavedListResponse:
        saved_items = await self._repository.list_items(session, user_id)
        return SavedListResponse(saved_list=saved_items)
