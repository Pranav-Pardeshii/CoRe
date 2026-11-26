"""Normalization, division mapping, and deduplication for extracted cutoff CSVs."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from etl.extract import normalize_name

logger = logging.getLogger(__name__)

PREFIX_TO_DIVISION: dict[str, str] = {
    "01": "Amravati Division",
    "02": "Aurangabad Division",
    "03": "Mumbai Division",
    "04": "Nagpur Division",
    "05": "Nashik Division",
    "06": "Pune Division",
    "11": "Amravati Division",
    "12": "Aurangabad Division",
    "13": "Mumbai Division",
    "14": "Nagpur Division",
    "15": "Nashik Division",
    "16": "Pune Division",
}

VALID_DIVISIONS: frozenset[str] = frozenset(PREFIX_TO_DIVISION.values())

FLAT_CSV_FIELDNAMES: tuple[str, ...] = (
    "college_code",
    "college_name",
    "branch_code",
    "branch_name",
    "status",
    "division",
    "year",
    "round",
    "level",
    "stage",
    "category",
    "rank",
    "percentile",
)


def normalize_college_code(raw_code: str) -> str:
    """Normalize a college code to a 5-character zero-padded string."""
    cleaned = raw_code.strip()
    if not cleaned:
        raise ValueError("Empty college_code encountered during transform.")
    return cleaned.zfill(5)


def map_division(college_code: str) -> str:
    """Map a 5-character college code to its Maharashtra DTE division."""
    prefix = college_code[:2]
    division = PREFIX_TO_DIVISION.get(prefix)
    if division is None:
        raise ValueError(f"Unmapped college code prefix: {prefix!r} (college_code={college_code})")
    return division


def transform_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize, map divisions, and deduplicate cutoff rows without losing leading zeros."""
    unmapped_prefixes: set[str] = set()
    seen_keys: set[tuple[str, str, str, str, str, str]] = set()
    transformed: list[dict[str, str]] = []
    duplicate_count = 0

    for row in raw_rows:
        college_code = normalize_college_code(row["college_code"])
        prefix = college_code[:2]
        division = PREFIX_TO_DIVISION.get(prefix)
        if division is None:
            unmapped_prefixes.add(prefix)
            continue

        branch_code = row["branch_code"].strip()
        year = str(row["year"]).strip()
        round_num = str(row["round"]).strip()
        level = row["level"].strip()
        stage = row["stage"].strip()
        category = row["category"].strip()

        composite_key = (branch_code, year, round_num, level, stage, category)
        if composite_key in seen_keys:
            duplicate_count += 1
            continue
        seen_keys.add(composite_key)

        transformed.append(
            {
                "college_code": college_code,
                "college_name": normalize_name(row["college_name"]),
                "branch_code": branch_code,
                "branch_name": normalize_name(row["branch_name"]),
                "status": normalize_name(row["status"]),
                "division": division,
                "year": year,
                "round": round_num,
                "level": level,
                "stage": stage,
                "category": category,
                "rank": str(row["rank"]).strip(),
                "percentile": str(row["percentile"]).strip(),
            }
        )

    if unmapped_prefixes:
        sorted_prefixes = ", ".join(sorted(unmapped_prefixes))
        raise ValueError(f"Unmapped college code prefix(es) encountered: {sorted_prefixes}")

    if duplicate_count:
        logger.warning("Deduplicated %d duplicate composite-key row(s).", duplicate_count)

    return transformed


def read_csv_strings(csv_path: Path) -> list[dict[str, str]]:
    """Read a CSV file with all fields strictly preserved as strings."""
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_flat_csv(rows: list[dict[str, str]], csv_path: Path) -> Path:
    """Write normalized flat cutoff rows to *csv_path*."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FLAT_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def transform_csvs(input_dir: Path, output_csv: Path) -> Path:
    """Merge all ``cutoff_*.csv`` files in *input_dir*, normalize, and write *output_csv*."""
    csv_files = sorted(input_dir.glob("cutoff_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No cutoff_*.csv files found in {input_dir}")

    raw_rows: list[dict[str, str]] = []
    for csv_file in csv_files:
        file_rows = read_csv_strings(csv_file)
        raw_rows.extend(file_rows)
        logger.info("Read %d rows from %s", len(file_rows), csv_file.name)

    transformed = transform_rows(raw_rows)
    write_flat_csv(transformed, output_csv)
    logger.info("Transformed %d unique rows -> %s", len(transformed), output_csv)
    return output_csv
