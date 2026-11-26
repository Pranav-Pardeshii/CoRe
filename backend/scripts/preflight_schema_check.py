"""Read-only preflight check for orphaned records before applying 0002/0003 migrations."""

import asyncio
import sys

from backend.app.core.config import get_settings
from backend.app.infrastructure.database.session import DatabaseManager
from sqlalchemy import text


async def run_preflight_checks() -> int:
    """Return 0 if no orphaned or invalid rows block migration, else 1."""
    settings = get_settings()
    db_manager = DatabaseManager()
    db_manager.init(settings)
    failures = 0

    try:
        async with db_manager.session_factory() as session:
            tables_result = await session.execute(text("SHOW TABLES"))
            tables = {row[0] for row in tables_result.all()}

            saved_table = "saved_list_items" if "saved_list_items" in tables else "saved_list"
            cutoffs_table = "admission_cutoffs" if "admission_cutoffs" in tables else "cutoffs"
            order_col = "sort_order" if saved_table == "saved_list_items" else "`rank`"

            checks = [
                (
                    f"orphaned {saved_table}.branch_code",
                    f"SELECT COUNT(*) FROM {saved_table} s "
                    "LEFT JOIN branches b ON s.branch_code = b.branch_code "
                    "WHERE b.branch_code IS NULL",
                ),
                (
                    f"orphaned {saved_table}.user_id",
                    f"SELECT COUNT(*) FROM {saved_table} s "
                    "LEFT JOIN users u ON s.user_id = u.id "
                    "WHERE u.id IS NULL",
                ),
                (
                    f"non-positive {saved_table}.{order_col}",
                    f"SELECT COUNT(*) FROM {saved_table} WHERE {order_col} < 1",
                ),
                (
                    f"out-of-range {cutoffs_table}.percentile",
                    f"SELECT COUNT(*) FROM {cutoffs_table} "
                    "WHERE percentile < 0 OR percentile > 100",
                ),
            ]

            for label, query in checks:
                count = int((await session.execute(text(query))).scalar_one())
                status_text = "OK" if count == 0 else f"FAIL ({count} rows)"
                print(f"[preflight] {label}: {status_text}")
                if count > 0:
                    failures += 1
    finally:
        await db_manager.dispose()

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_preflight_checks()))
