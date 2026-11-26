import csv
import logging
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / "backend" / ".env")


def _env_or_legacy(primary: str, legacy: str, default: str | None = None) -> str | None:
    return os.getenv(primary) or os.getenv(legacy) or default


def load_cutoffs() -> None:
    """Load deduplicated colleges, branches, and admission_cutoffs into MySQL."""
    flat_csv_path = REPO_ROOT / "cutoffs_flat.csv"
    logger.info("Reading flat CSV from %s", flat_csv_path)
    with flat_csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    logger.info("Loaded %d rows", len(rows))

    colleges: dict[str, tuple[str, str, str, str]] = {}
    branches: dict[str, tuple[str, str, str]] = {}
    admission_cutoffs: list[tuple[str, int, int, str, str, str, int, float]] = []

    for row in rows:
        college_code = row["college_code"]
        if college_code not in colleges:
            colleges[college_code] = (
                college_code,
                row["college_name"],
                row["status"],
                row["division"],
            )

        branch_code = row["branch_code"]
        if branch_code not in branches:
            branches[branch_code] = (
                branch_code,
                row["branch_name"],
                college_code,
            )

        admission_cutoffs.append(
            (
                branch_code,
                int(row["year"]),
                int(row["round"]),
                row["level"],
                row["stage"],
                row["category"],
                int(row["rank"]),
                float(row["percentile"]),
            )
        )

    db_config: dict[str, object] = {
        "host": _env_or_legacy("CORE_DB_HOST", "DB_HOST"),
        "port": int(_env_or_legacy("CORE_DB_PORT", "DB_PORT", "3306") or "3306"),
        "user": _env_or_legacy("CORE_DB_USER", "DB_USER"),
        "password": _env_or_legacy("CORE_DB_PASS", "DB_PASS"),
        "database": _env_or_legacy("CORE_DB_NAME", "DB_NAME"),
        "use_pure": True,
    }
    ssl_ca = _env_or_legacy("CORE_DB_SSL_CA", "DB_SSL_CA")
    if ssl_ca:
        db_config["ssl_ca"] = ssl_ca

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    try:
        # Transitional DDL guard until Alembic is stamped on all target environments.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS colleges (
                college_code VARCHAR(10) PRIMARY KEY,
                college_name VARCHAR(300) NOT NULL,
                status VARCHAR(300),
                division VARCHAR(100)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS branches (
                branch_code VARCHAR(15) PRIMARY KEY,
                branch_name VARCHAR(300) NOT NULL,
                college_code VARCHAR(10) NOT NULL,
                FOREIGN KEY (college_code) REFERENCES colleges(college_code)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admission_cutoffs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                branch_code VARCHAR(15) NOT NULL,
                admission_year SMALLINT NOT NULL,
                cap_round TINYINT NOT NULL,
                level VARCHAR(10) NOT NULL,
                admission_stage VARCHAR(5) NOT NULL,
                category VARCHAR(20) NOT NULL,
                merit_rank INT NOT NULL,
                percentile FLOAT NOT NULL,
                FOREIGN KEY (branch_code) REFERENCES branches(branch_code),
                UNIQUE KEY uq_admission_cutoffs_composite (
                    branch_code, admission_year, cap_round, level, admission_stage, category
                )
            )
            """
        )
        connection.commit()

        cursor.executemany(
            """
            INSERT IGNORE INTO colleges (college_code, college_name, status, division)
            VALUES (%s, %s, %s, %s)
            """,
            list(colleges.values()),
        )
        connection.commit()
        logger.info("Inserted %d colleges", cursor.rowcount)

        cursor.executemany(
            """
            INSERT IGNORE INTO branches (branch_code, branch_name, college_code)
            VALUES (%s, %s, %s)
            """,
            list(branches.values()),
        )
        connection.commit()
        logger.info("Inserted %d branches", cursor.rowcount)

        cursor.executemany(
            """
            INSERT IGNORE INTO admission_cutoffs (
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
            """,
            admission_cutoffs,
        )
        connection.commit()
        logger.info("Inserted %d admission_cutoffs", cursor.rowcount)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_cutoffs()
