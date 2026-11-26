from unittest.mock import AsyncMock

import pytest
from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError, ConflictError, NotFoundError, UnauthorizedError
from backend.app.core.security import create_access_token
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from backend.app.modules.catalog.repository import BranchCollegeInfo
from backend.app.modules.saved_lists.schemas import SavedListReorderRequest
from backend.app.modules.saved_lists.service import MAX_SAVED_LIST_ITEMS, SavedListService
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def test_reorder_schema_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        SavedListReorderRequest(ordered_list=[1, 1, 2])


async def test_saved_list_create_allocates_rank_and_handles_duplicates() -> None:
    repo = AsyncMock()
    catalog_repo = AsyncMock()
    catalog_repo.get_branch_with_college.return_value = BranchCollegeInfo(
        college_code="06271",
        college_name="COEP",
        branch_name="Computer Engineering",
    )
    repo.lock_user_for_update.return_value = True
    repo.get_count_and_max_sort_order.return_value = (2, 2)
    session = AsyncMock()
    service = SavedListService(repository=repo, catalog_repository=catalog_repo)

    res = await service.create_item(session, user_id=5, branch_code="0627124510")
    assert res.message == "Item saved successfully."
    repo.lock_user_for_update.assert_awaited_once_with(session, 5)
    repo.create_item.assert_awaited_once_with(
        session,
        user_id=5,
        college_code="06271",
        branch_code="0627124510",
        college_name="COEP",
        branch_name="Computer Engineering",
        sort_order=3,
    )
    session.commit.assert_awaited_once()

    # Duplicate save -> ConflictError (409) + rollback
    session.reset_mock()
    repo.create_item.side_effect = IntegrityError("INSERT", {}, Exception("Duplicate entry"))
    with pytest.raises(ConflictError) as exc_info:
        await service.create_item(session, user_id=5, branch_code="0627124510")
    assert exc_info.value.status_code == 409
    session.rollback.assert_awaited_once()


async def test_saved_list_enforces_max_items_and_user_existence() -> None:
    repo = AsyncMock()
    catalog_repo = AsyncMock()
    catalog_repo.get_branch_with_college.return_value = BranchCollegeInfo(
        college_code="06271",
        college_name="COEP",
        branch_name="Computer Engineering",
    )
    session = AsyncMock()
    service = SavedListService(repository=repo, catalog_repository=catalog_repo)

    repo.lock_user_for_update.return_value = False
    with pytest.raises(UnauthorizedError):
        await service.create_item(session, user_id=5, branch_code="0627124510")

    repo.lock_user_for_update.return_value = True
    repo.get_count_and_max_sort_order.return_value = (MAX_SAVED_LIST_ITEMS, MAX_SAVED_LIST_ITEMS)
    with pytest.raises(AppError, match="limit"):
        await service.create_item(session, user_id=5, branch_code="0627124510")


async def test_saved_list_delete_enforces_ownership() -> None:
    repo = AsyncMock()
    repo.lock_user_for_update.return_value = True
    repo.delete_item.return_value = 0
    session = AsyncMock()
    service = SavedListService(repository=repo)

    with pytest.raises(NotFoundError):
        await service.delete_item(session, user_id=5, item_id=99)
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_saved_list_reorder_uses_bulk_update_and_validates_membership() -> None:
    repo = AsyncMock()
    repo.lock_user_for_update.return_value = True
    repo.get_owned_ids_for_update.return_value = {1, 2}
    session = AsyncMock()
    service = SavedListService(repository=repo)

    # Duplicate IDs rejected
    with pytest.raises(AppError):
        await service.reorder(session, user_id=5, ordered_list=[1, 1, 2])

    # Foreign / missing ID rejected
    with pytest.raises(AppError):
        await service.reorder(session, user_id=5, ordered_list=[1, 3])
    session.rollback.assert_awaited()

    # Exact permutation succeeds with a single bulk update
    session.reset_mock()
    res = await service.reorder(session, user_id=5, ordered_list=[2, 1])
    assert res.message == "Bingo! list reordered successfully!"
    repo.bulk_update_sort_orders.assert_awaited_once_with(
        session,
        user_id=5,
        ordered_list=[2, 1],
    )
    session.commit.assert_awaited_once()


def test_saved_list_endpoints_require_auth(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    with TestClient(app) as client:
        assert client.get("/saved-lists/").status_code == 401
        assert client.post("/saved-lists/", json={"branch_code": "X"}).status_code == 401
        assert client.put("/saved-lists/", json={"ordered_list": [1]}).status_code == 401
        assert client.delete("/saved-lists/1").status_code == 401

        # Authenticated duplicate reorder payload is rejected with 422
        token = create_access_token({"sub": "5"}, secret_key=test_settings.SECRET_KEY)
        resp = client.put(
            "/saved-lists/",
            json={"ordered_list": [1, 1]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
        assert resp.headers.get("Cache-Control") == "no-store"
