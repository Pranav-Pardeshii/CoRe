from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_current_user_id
from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.saved_lists.schemas import (
    SavedListCreateRequest,
    SavedListMessageResponse,
    SavedListReorderRequest,
    SavedListResponse,
)
from backend.app.modules.saved_lists.service import SavedListService

router = APIRouter(prefix="/saved-lists", tags=["Saved List"])
_saved_list_service = SavedListService()


@router.post("/", response_model=SavedListMessageResponse)
async def create_item(
    save_request: SavedListCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id),
) -> SavedListMessageResponse:
    return await _saved_list_service.create_item(
        session,
        user_id=current_user_id,
        branch_code=save_request.branch_code,
    )


@router.delete("/{id}", response_model=SavedListMessageResponse)
async def delete_item(
    id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id),
) -> SavedListMessageResponse:
    return await _saved_list_service.delete_item(
        session,
        user_id=current_user_id,
        item_id=id,
    )


@router.put("/", response_model=SavedListMessageResponse)
async def reorder(
    reorder_request: SavedListReorderRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id),
) -> SavedListMessageResponse:
    return await _saved_list_service.reorder(
        session,
        user_id=current_user_id,
        ordered_list=reorder_request.ordered_list,
    )


@router.get("/", response_model=SavedListResponse)
async def get_saved_list(
    session: AsyncSession = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id),
) -> SavedListResponse:
    return await _saved_list_service.get_saved_list(session, user_id=current_user_id)
