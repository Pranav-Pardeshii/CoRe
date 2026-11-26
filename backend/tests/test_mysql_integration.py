import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.modules.catalog.models import AdmissionCutoff, Branch, College
from backend.tests.conftest import (
    get_validated_test_database_url,
    require_destructive_test_opt_in,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration


def _run_alembic(test_url: str, action: str, revision: str = "head") -> None:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", test_url)
    if action == "upgrade":
        command.upgrade(cfg, revision)
    elif action == "downgrade":
        command.downgrade(cfg, revision)
    elif action == "check":
        command.check(cfg)


async def _reset_test_schema(test_url: str) -> None:
    """Drop all known legacy/current tables so each integration test starts from an empty DB."""
    engine = create_async_engine(test_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "DROP TABLE IF EXISTS saved_list_items, saved_list, "
                    "admission_cutoffs, cutoffs, branches, colleges, users, alembic_version"
                )
            )
    finally:
        await engine.dispose()


async def test_legacy_0001_to_0004_migration_and_downgrade_roundtrip() -> None:
    """Verify upgrading 0001 -> head, alembic check, downgrade to 0003, and re-upgrade."""
    test_url = get_validated_test_database_url()
    require_destructive_test_opt_in()
    await _reset_test_schema(test_url)
    await asyncio.to_thread(_run_alembic, test_url, "upgrade", "0001_initial_schema")

    engine = create_async_engine(test_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO colleges (college_code, college_name, status, division) "
                    "VALUES ('06271', 'PICT', 'Un-Aided', 'Pune Division')"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO branches (branch_code, branch_name, college_code) "
                    "VALUES ('0627124510', 'Computer Engineering', '06271')"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO cutoffs "
                    "(branch_code, year, round, level, stage, category, `rank`, percentile) "
                    "VALUES ('0627124510', 2024, 1, 'SL', 'I', 'GOPENS', 500, 99.1)"
                )
            )
            await conn.execute(
                text("INSERT INTO users (username, password) VALUES ('legacy_user', 'hash')")
            )
            user_id = (
                await conn.execute(text("SELECT id FROM users WHERE username = 'legacy_user'"))
            ).scalar_one()
            await conn.execute(
                text(
                    "INSERT INTO saved_list "
                    "(user_id, college_code, branch_code, college_name, branch_name, `rank`) "
                    "VALUES (:uid, '06271', '0627124510', 'PICT', 'Computer Engineering', 1)"
                ),
                {"uid": user_id},
            )
    finally:
        await engine.dispose()

    await asyncio.to_thread(_run_alembic, test_url, "upgrade", "head")
    await asyncio.to_thread(_run_alembic, test_url, "check")

    await asyncio.to_thread(_run_alembic, test_url, "downgrade", "0003_password_hash_and_fk")
    await asyncio.to_thread(_run_alembic, test_url, "upgrade", "head")
    await asyncio.to_thread(_run_alembic, test_url, "check")

    verify_engine = create_async_engine(test_url)
    try:
        async with verify_engine.connect() as conn:
            cutoff_row = (
                await conn.execute(
                    text(
                        "SELECT admission_year, cap_round, admission_stage, merit_rank, percentile "
                        "FROM admission_cutoffs WHERE branch_code = '0627124510'"
                    )
                )
            ).one()
            assert tuple(cutoff_row[:4]) == (2024, 1, "I", 500)
            assert isinstance(cutoff_row[4], Decimal)

            saved_row = (
                await conn.execute(
                    text(
                        "SELECT branch_code, sort_order FROM saved_list_items "
                        "WHERE branch_code = '0627124510'"
                    )
                )
            ).one()
            assert tuple(saved_row) == ("0627124510", 1)
    finally:
        await verify_engine.dispose()


async def test_mysql_migrations_and_end_to_end_flows() -> None:
    test_url = get_validated_test_database_url()
    require_destructive_test_opt_in()
    await _reset_test_schema(test_url)
    await asyncio.to_thread(_run_alembic, test_url, "upgrade", "head")
    await asyncio.to_thread(_run_alembic, test_url, "check")

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DB_HOST="127.0.0.1",
        DB_USER="root",
        DB_PASS="",
        DB_NAME="core_test",
        SECRET_KEY="integration-test-secret-at-least-32-chars",
    )
    app = create_app(settings=settings, database_url_override=test_url)

    async with app.router.lifespan_context(app):
        db_manager = app.state.db_manager
        async with db_manager.session_factory() as session:
            await session.execute(text("DELETE FROM saved_list_items"))
            await session.execute(text("DELETE FROM admission_cutoffs"))
            await session.execute(text("DELETE FROM branches"))
            await session.execute(text("DELETE FROM colleges"))
            await session.execute(text("DELETE FROM users"))

            session.add(
                College(
                    college_code="06271",
                    college_name="Pune Institute of Computer Technology",
                    status="Un-Aided",
                    division="Pune Division",
                )
            )
            session.add_all(
                [
                    Branch(
                        branch_code="0627124510",
                        branch_name="Computer Engineering",
                        college_code="06271",
                    ),
                    Branch(
                        branch_code="0627124610",
                        branch_name="Information Technology",
                        college_code="06271",
                    ),
                    Branch(
                        branch_code="0627137210",
                        branch_name="Electronics and Telecommunication",
                        college_code="06271",
                    ),
                ]
            )
            session.add_all(
                [
                    AdmissionCutoff(
                        branch_code="0627124510",
                        admission_year=2024,
                        cap_round=1,
                        level="SL",
                        admission_stage="I",
                        category="GOPENS",
                        merit_rank=500,
                        percentile=Decimal("99.1234567"),
                    ),
                    AdmissionCutoff(
                        branch_code="0627124510",
                        admission_year=2025,
                        cap_round=1,
                        level="HU_HU",
                        admission_stage="I",
                        category="GOPENS",
                        merit_rank=600,
                        percentile=Decimal("98.5000000"),
                    ),
                    AdmissionCutoff(
                        branch_code="0627124510",
                        admission_year=2023,
                        cap_round=1,
                        level="SL",
                        admission_stage="I",
                        category="GOPENS",
                        merit_rank=900,
                        percentile=Decimal("90.0000000"),
                    ),
                    AdmissionCutoff(
                        branch_code="0627124510",
                        admission_year=2025,
                        cap_round=2,
                        level="SL",
                        admission_stage="II",
                        category="GOPENS",
                        merit_rank=800,
                        percentile=Decimal("95.0000000"),
                    ),
                ]
            )
            await session.commit()

            # Verify exact DECIMAL(10, 7) precision without float drift
            stored_percentile = (
                await session.execute(
                    text(
                        "SELECT percentile FROM admission_cutoffs "
                        "WHERE branch_code = '0627124510' AND admission_year = 2024"
                    )
                )
            ).scalar_one()
            assert stored_percentile == Decimal("99.1234567")

            # Verify FK constraint on branches -> colleges
            session.add(
                Branch(
                    branch_code="9999900001",
                    branch_name="Invalid",
                    college_code="99999",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            # Verify composite unique constraint on admission_cutoffs
            session.add(
                AdmissionCutoff(
                    branch_code="0627124510",
                    admission_year=2024,
                    cap_round=1,
                    level="SL",
                    admission_stage="I",
                    category="GOPENS",
                    merit_rank=501,
                    percentile=Decimal("99.0000000"),
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            assert (await client.get("/")).status_code == 200
            ping_resp = await client.get("/ping")
            assert ping_resp.status_code == 200
            assert ping_resp.json() == {"status": "ok"}
            assert (await client.get("/health/live")).status_code == 200
            assert (await client.get("/health/ready")).status_code == 200

            for user in ("alice", "bob"):
                reg = await client.post(
                    "/auth/register",
                    json={"username": user, "password": "password123"},
                )
                assert reg.status_code == 200

            login_alice = await client.post(
                "/auth/login",
                data={"username": "alice", "password": "password123"},
            )
            assert login_alice.status_code == 200
            alice_headers = {"Authorization": f"Bearer {login_alice.json()['access_token']}"}

            login_bob = await client.post(
                "/auth/login",
                data={"username": "bob", "password": "password123"},
            )
            assert login_bob.status_code == 200
            bob_headers = {"Authorization": f"Bearer {login_bob.json()['access_token']}"}

            rec = await client.get(
                "/recommender/",
                params={
                    "percentile": 98.7,
                    "category": "GOPENS",
                    "branch": "Computer Engineering",
                    "division": "Pune Division",
                },
            )
            assert rec.status_code == 200
            rec_data = rec.json()
            assert rec_data["count"] == 1
            assert rec_data["eligible_colleges"][0]["min_cutoff"] == 98.5

            # Pagination page=2 returns empty list with accurate count
            rec_page2 = await client.get(
                "/recommender/",
                params={
                    "percentile": 98.7,
                    "category": "GOPENS",
                    "branch": "All",
                    "division": "All",
                    "page": 2,
                    "page_size": 5,
                },
            )
            assert rec_page2.status_code == 200
            assert rec_page2.json() == {"eligible_colleges": [], "count": 1}

            # Trends with multiple levels and optional level filter
            tr = await client.get(
                "/trends/",
                params={"branch_code": "0627124510", "category": "All"},
            )
            assert tr.status_code == 200
            assert tr.json()["count"] == 3
            assert {p["level"] for p in tr.json()["trends"]} == {"SL", "HU_HU"}

            tr_filtered = await client.get(
                "/trends/",
                params={"branch_code": "0627124510", "category": "All", "level": "HU_HU"},
            )
            assert tr_filtered.status_code == 200
            assert tr_filtered.json()["count"] == 1

            # Catalog filters endpoint
            cat_filters = await client.get("/catalog/filters")
            assert cat_filters.status_code == 200
            assert cat_filters.json()["categories"] == ["GOPENS"]
            assert cat_filters.json()["years"] == [2025, 2024, 2023]

            # Saved list create + 409 duplicate + multi-item bulk reorder
            for code in ("0627124510", "0627124610", "0627137210"):
                save_resp = await client.post(
                    "/saved-lists/",
                    json={"branch_code": code},
                    headers=alice_headers,
                )
                assert save_resp.status_code == 200

            dup = await client.post(
                "/saved-lists/",
                json={"branch_code": "0627124510"},
                headers=alice_headers,
            )
            assert dup.status_code == 409

            alice_items = (await client.get("/saved-lists/", headers=alice_headers)).json()[
                "saved_list"
            ]
            assert len(alice_items) == 3
            id1, id2, id3 = [item["id"] for item in alice_items]

            bob_items = (await client.get("/saved-lists/", headers=bob_headers)).json()[
                "saved_list"
            ]
            assert bob_items == []
            assert (
                await client.delete(f"/saved-lists/{id1}", headers=bob_headers)
            ).status_code == 404
            assert (
                await client.put(
                    "/saved-lists/",
                    json={"ordered_list": [id1]},
                    headers=bob_headers,
                )
            ).status_code == 400

            # Reorder [id1, id2, id3] -> [id3, id1, id2]
            assert (
                await client.put(
                    "/saved-lists/",
                    json={"ordered_list": [id3, id1, id2]},
                    headers=alice_headers,
                )
            ).status_code == 200

            reordered_items = (await client.get("/saved-lists/", headers=alice_headers)).json()[
                "saved_list"
            ]
            assert [item["id"] for item in reordered_items] == [id3, id1, id2]

            assert (
                await client.delete(f"/saved-lists/{id1}", headers=alice_headers)
            ).status_code == 200
