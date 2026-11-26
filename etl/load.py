"""Chunked idempotent MySQL loader for CoRe ETL."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import mysql.connector

from etl.config import DatabaseConfig, load_db_config
from etl.transform import read_csv_strings
from etl.validate import ValidationError, format_validation_summary, validate_rows

logger = logging.getLogger(__name__)

REQUIRED_TABLES: frozenset[str] = frozenset(
    {"alembic_version", "colleges", "branches", "admission_cutoffs"}
)
DEFAULT_BATCH_SIZE = 2000

UPSERT_COLLEGES_SQL = """
INSERT INTO colleges (college_code, college_name, status, division)
VALUES (%s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    college_name = VALUES(college_name),
    status = VALUES(status),
    division = VALUES(division)
"""

UPSERT_BRANCHES_SQL = """
INSERT INTO branches (branch_code, branch_name, college_code)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE
    branch_name = VALUES(branch_name),
    college_code = VALUES(college_code)
"""

UPSERT_CUTOFFS_SQL = """
INSERT INTO admission_cutoffs (
    branch_code,
    admission_year,
    cap_round,
    level,
    admission_stage,
    category,
    merit_rank,
    percentile
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    merit_rank = VALUES(merit_rank),
    percentile = VALUES(percentile)
"""


def chunked[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield successive chunks of length *size* from *items*."""
    if size <= 0:
        raise ValueError(f"batch_size must be positive, got {size}")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def prepare_records(
    rows: list[dict[str, str]],
) -> tuple[
    list[tuple[str, str, str, str]],
    list[tuple[str, str, str]],
    list[tuple[str, int, int, str, str, str, int, float]],
]:
    """Build deduplicated college/branch tuples and cutoff tuples from validated rows."""
    colleges: dict[str, tuple[str, str, str, str]] = {}
    branches: dict[str, tuple[str, str, str]] = {}
    cutoffs: list[tuple[str, int, int, str, str, str, int, float]] = []

    for row in rows:
        college_code = row["college_code"].strip()
        if college_code not in colleges:
            colleges[college_code] = (
                college_code,
                row["college_name"].strip(),
                row["status"].strip(),
                row["division"].strip(),
            )

        branch_code = row["branch_code"].strip()
        if branch_code not in branches:
            branches[branch_code] = (
                branch_code,
                row["branch_name"].strip(),
                college_code,
            )

        year_val = int((row.get("admission_year") or row["year"]).strip())
        round_val = int((row.get("cap_round") or row["round"]).strip())
        stage_val = (row.get("admission_stage") or row["stage"]).strip()
        rank_val = int((row.get("merit_rank") or row["rank"]).strip())

        cutoffs.append(
            (
                branch_code,
                year_val,
                round_val,
                row["level"].strip(),
                stage_val,
                row["category"].strip(),
                rank_val,
                float(row["percentile"].strip()),
            )
        )

    return list(colleges.values()), list(branches.values()), cutoffs


def verify_alembic_tables(cursor: Any) -> None:
    """Ensure Alembic-managed tables exist before loading."""
    cursor.execute("SHOW TABLES")
    existing_tables = {row[0] for row in cursor.fetchall()}
    missing_tables = sorted(REQUIRED_TABLES - existing_tables)
    if missing_tables:
        raise RuntimeError(
            f"Database schema is not initialized for Alembic (missing: {missing_tables}). "
            "Run 'uv run alembic -c backend/alembic.ini upgrade head' before running ETL."
        )


def _execute_chunked_upsert(
    cursor: Any,
    connection: Any,
    sql: str,
    records: Sequence[tuple[Any, ...]],
    batch_size: int,
    label: str,
) -> None:
    total = len(records)
    for batch_num, batch in enumerate(chunked(records, batch_size), start=1):
        cursor.executemany(sql, list(batch))
        connection.commit()
        logger.info("Upserted %s batch %d (%d rows)", label, batch_num, len(batch))
    logger.info("Completed %s upsert: %d total records processed", label, total)


def _log_table_counts(cursor: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in ("colleges", "branches", "admission_cutoffs"):
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = cursor.fetchone()
        count = int(row[0]) if row else 0
        counts[table_name] = count
        logger.info("Post-load count %-18s: %d", table_name, count)
    return counts


def load_csv_to_db(
    csv_path: Path,
    *,
    db_config: DatabaseConfig | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> dict[str, int]:
    """Validate *csv_path* and load colleges, branches, and admission_cutoffs in chunks."""
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows = read_csv_strings(csv_path)
    report = validate_rows(rows)
    logger.info("\n%s", format_validation_summary(report))
    if not report.is_valid:
        raise ValidationError(report)

    colleges, branches, cutoffs = prepare_records(rows)
    logger.info(
        "Prepared %d colleges, %d branches, %d admission_cutoffs (batch_size=%d)",
        len(colleges),
        len(branches),
        len(cutoffs),
        batch_size,
    )

    if dry_run:
        logger.info("Dry-run enabled: skipping MySQL connection and writes.")
        return {
            "colleges": len(colleges),
            "branches": len(branches),
            "admission_cutoffs": len(cutoffs),
        }

    cfg = db_config or load_db_config()
    connection = mysql.connector.connect(**cfg.to_connector_kwargs())
    cursor = connection.cursor()
    try:
        verify_alembic_tables(cursor)
        _execute_chunked_upsert(
            cursor, connection, UPSERT_COLLEGES_SQL, colleges, batch_size, "colleges"
        )
        _execute_chunked_upsert(
            cursor, connection, UPSERT_BRANCHES_SQL, branches, batch_size, "branches"
        )
        _execute_chunked_upsert(
            cursor, connection, UPSERT_CUTOFFS_SQL, cutoffs, batch_size, "admission_cutoffs"
        )
        return _log_table_counts(cursor)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
