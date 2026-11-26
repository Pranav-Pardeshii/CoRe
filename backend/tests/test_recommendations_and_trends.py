from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.core.config import Settings
from backend.app.infrastructure.database.session import get_db_session
from backend.app.main import create_app
from backend.app.modules.recommendations.schemas import RecommenderQuery
from backend.app.modules.recommendations.service import RecommendationsService
from backend.app.modules.trends.schemas import TrendsQuery
from backend.app.modules.trends.service import TrendsService
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_recommender_query_accepts_zero_percentile_and_validates_bounds() -> None:
    q = RecommenderQuery(percentile=0.0, category="All", branch="All", division="All")
    assert q.percentile == 0.0
    assert q.page == 1
    assert q.page_size == 10

    with pytest.raises(ValidationError):
        RecommenderQuery(percentile=-0.1, category="All", branch="All", division="All")
    with pytest.raises(ValidationError):
        RecommenderQuery(percentile=100.1, category="All", branch="All", division="All")
    with pytest.raises(ValidationError):
        RecommenderQuery(percentile=50, category="All", branch="All", division="All", page_size=4)


async def test_recommendations_service_maps_all_filters_and_pagination(
    test_settings: Settings,
) -> None:
    repo = AsyncMock()
    repo.find_eligible_colleges.return_value = ([], 0)
    service = RecommendationsService(repository=repo)
    session = AsyncMock()

    result = await service.get_recommendations(
        session,
        RecommenderQuery(
            percentile=95.5,
            category="All",
            branch="Computer Engineering",
            division="All",
            page=2,
            page_size=15,
        ),
        settings=test_settings,
    )

    assert result.count == 0
    assert result.eligible_colleges == []
    repo.find_eligible_colleges.assert_awaited_once_with(
        session,
        percentile=95.5,
        category=None,
        branch="Computer Engineering",
        division=None,
        limit=15,
        offset=15,
        years=test_settings.RECOMMENDER_YEARS,
    )


async def test_trends_service_defaults_all_category_to_gopens() -> None:
    repo = AsyncMock()
    repo.get_branch_trends.return_value = []
    service = TrendsService(repository=repo)
    session = AsyncMock()

    result = await service.get_trends(
        session,
        TrendsQuery(branch_code="0627124510", category="All", level="SL"),
    )

    assert result.branch_code == "0627124510"
    assert result.count == 0
    repo.get_branch_trends.assert_awaited_once_with(
        session,
        branch_code="0627124510",
        category="GOPENS",
        level="SL",
    )


def test_recommender_trends_and_catalog_http_contracts(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        database_url_override="mysql+asyncmy://u:p@localhost:3306/core_test",
    )
    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    with TestClient(app) as client:
        years_res = MagicMock()
        years_res.all.return_value = [(2025,), (2024,)]
        empty_rows_res = MagicMock()
        empty_rows_res.all.return_value = []
        mock_session.execute.side_effect = [years_res, empty_rows_res]

        rec_resp = client.get(
            "/recommender/",
            params={"percentile": 0, "category": "All", "branch": "All", "division": "All"},
        )
        assert rec_resp.status_code == 200
        assert rec_resp.headers["Cache-Control"] == "public, max-age=3600"
        assert rec_resp.json() == {"eligible_colleges": [], "count": 0}

        trends_res = MagicMock()
        trends_res.all.return_value = [(2024, 1, "SL", 98.5), (2025, 1, "SL", 99.1)]
        mock_session.execute.side_effect = None
        mock_session.execute.return_value = trends_res

        tr_resp = client.get(
            "/trends/",
            params={"branch_code": "0627124510", "category": "All"},
        )
        assert tr_resp.status_code == 200
        assert tr_resp.headers["Cache-Control"] == "public, max-age=3600"
        assert tr_resp.json() == {
            "branch_code": "0627124510",
            "count": 2,
            "trends": [
                {"year": 2024, "round": 1, "level": "SL", "percentile": 98.5},
                {"year": 2025, "round": 1, "level": "SL", "percentile": 99.1},
            ],
        }

        cat_res = MagicMock()
        cat_res.all.return_value = [("GOPENS",), ("TFWS",)]
        br_res = MagicMock()
        br_res.all.return_value = [("Computer Engineering",)]
        div_res = MagicMock()
        div_res.all.return_value = [("Pune Division",)]
        yr_res = MagicMock()
        yr_res.all.return_value = [(2025,), (2024,)]
        lvl_res = MagicMock()
        lvl_res.all.return_value = [("SL",)]
        mock_session.execute.side_effect = [cat_res, br_res, div_res, yr_res, lvl_res]

        filters_resp = client.get("/catalog/filters")
        assert filters_resp.status_code == 200
        assert filters_resp.headers["Cache-Control"] == "public, max-age=3600"
        assert filters_resp.json() == {
            "categories": ["GOPENS", "TFWS"],
            "branches": ["Computer Engineering"],
            "divisions": ["Pune Division"],
            "years": [2025, 2024],
            "levels": ["SL"],
        }
