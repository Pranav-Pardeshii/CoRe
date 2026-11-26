from unittest.mock import AsyncMock

import pytest
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import AppError, ConflictError, NotFoundError
from backend.app.core.security import create_access_token
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from backend.app.modules.catalog.repository import BranchCollegeInfo
from backend.app.modules.saved_lists.schemas import SavedListReorderRequest
from backend.app.modules.saved_lists.service import SavedListService
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
    repo.get_max_sort_order_for_update.return_value = 2
    session = AsyncMock()
    service = SavedListService(repository=repo, catalog_repository=catalog_repo)

    res = await service.create_item(session, user_id=5, branch_code="0627124510")
    assert res.message == "Item saved successfully."
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

    # Duplicate save -> ConflictError + rollback
    session.reset_mock()
    repo.create_item.side_effect = IntegrityError("INSERT", {}, Exception("Duplicate"))
    with pytest.raises(ConflictError):
        await service.create_item(session, user_id=5, branch_code="0627124510")
    session.rollback.assert_awaited_once()


async def test_saved_list_delete_enforces_ownership() -> None:
    repo = AsyncMock()
    repo.delete_item.return_value = 0
    session = AsyncMock()
    service = SavedListService(repository=repo)

    with pytest.raises(NotFoundError):
        await service.delete_item(session, user_id=5, item_id=99)
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_saved_list_reorder_validates_exact_membership_and_uniqueness() -> None:
    repo = AsyncMock()
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

    # Exact permutation succeeds
    session.reset_mock()
    res = await service.reorder(session, user_id=5, ordered_list=[2, 1])
    assert res.message == "Bingo! list reordered successfully!"
    assert repo.update_sort_order.await_count == 2
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
    app.dependency_overrides[get_settings] = lambda: test_settings

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
