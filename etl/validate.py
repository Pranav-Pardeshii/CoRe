"""Strict fail-closed pre-load data quality gate for CoRe ETL."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from etl.extract import is_valid_category_code
from etl.transform import VALID_DIVISIONS, read_csv_strings

logger = logging.getLogger(__name__)

COLLEGE_CODE_RE = re.compile(r"^\d{5}$")
STRICT_INT_RE = re.compile(r"^-?\d+$")
VALID_LEVELS: frozenset[str] = frozenset({"HU_HU", "HU_OHU", "OHU_HU", "OHU_OHU", "SL"})


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    """Single row-level validation failure."""

    row_number: int
    reason: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Summary of a validation run."""

    total_rows: int
    valid_rows: int
    failures: tuple[ValidationFailure, ...]

    @property
    def is_valid(self) -> bool:
        """Return True if all rows passed validation."""
        return len(self.failures) == 0 and self.total_rows > 0


class ValidationError(ValueError):
    """Raised when pre-load validation fails."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        sample = "; ".join(f"row {f.row_number}: {f.reason}" for f in report.failures[:10])
        if report.total_rows == 0:
            msg = "Validation failed: dataset contains 0 rows."
        else:
            msg = (
                f"Validation failed: {len(report.failures)} error(s) across "
                f"{report.total_rows} rows. Sample: {sample}"
            )
        super().__init__(msg)


def _parse_strict_int(raw: str, field_name: str) -> int:
    value = raw.strip()
    if not STRICT_INT_RE.match(value):
        raise ValueError(f"{field_name} must be an integer, got {raw!r}")
    return int(value)


def validate_rows(rows: list[dict[str, str]]) -> ValidationReport:
    """Validate all cutoff rows against schema, domain, and uniqueness rules."""
    failures: list[ValidationFailure] = []
    seen_keys: set[tuple[str, int, int, str, str, str]] = set()
    valid_count = 0

    for idx, row in enumerate(rows, start=1):
        row_errors: list[str] = []

        college_code = row.get("college_code", "").strip()
        branch_code = row.get("branch_code", "").strip()
        division = row.get("division", "").strip()
        level = row.get("level", "").strip()
        admission_stage = (row.get("admission_stage") or row.get("stage") or "").strip()
        category = row.get("category", "").strip()

        if not COLLEGE_CODE_RE.match(college_code):
            row_errors.append(f"invalid college_code {college_code!r} (expected 5 digits)")

        if not branch_code:
            row_errors.append("empty branch_code")
        else:
            if college_code and not branch_code.startswith(college_code):
                row_errors.append(
                    f"branch_code {branch_code!r} does not start with college_code {college_code!r}"
                )
            if len(branch_code) > 15:
                row_errors.append(f"branch_code {branch_code!r} exceeds max length 15")

        if division not in VALID_DIVISIONS:
            row_errors.append(f"invalid division {division!r}")

        admission_year: int | None = None
        year_raw = row.get("admission_year") or row.get("year") or ""
        try:
            admission_year = _parse_strict_int(year_raw, "admission_year")
            if not (2020 <= admission_year <= 2035):
                row_errors.append(f"admission_year {admission_year} out of range [2020, 2035]")
        except ValueError as exc:
            row_errors.append(str(exc))

        cap_round: int | None = None
        round_raw = row.get("cap_round") or row.get("round") or ""
        try:
            cap_round = _parse_strict_int(round_raw, "cap_round")
            if not (1 <= cap_round <= 10):
                row_errors.append(f"cap_round {cap_round} out of range [1, 10]")
        except ValueError as exc:
            row_errors.append(str(exc))

        if not admission_stage or len(admission_stage) > 5:
            row_errors.append(f"invalid admission_stage {admission_stage!r}")

        if level not in VALID_LEVELS:
            row_errors.append(f"invalid level {level!r}")

        if not is_valid_category_code(category):
            row_errors.append(f"invalid category {category!r}")

        rank_raw = row.get("merit_rank") or row.get("rank") or ""
        try:
            merit_rank = _parse_strict_int(rank_raw, "merit_rank")
            if merit_rank <= 0:
                row_errors.append(f"merit_rank {merit_rank} must be > 0")
        except ValueError as exc:
            row_errors.append(str(exc))

        perc_raw = row.get("percentile", "").strip()
        try:
            percentile = Decimal(perc_raw)
            if (
                not percentile.is_finite()
                or percentile < Decimal("0")
                or percentile > Decimal("100")
            ):
                row_errors.append(f"percentile {perc_raw!r} out of range [0, 100]")
        except (InvalidOperation, ValueError):
            row_errors.append(f"invalid percentile {perc_raw!r}")

        if admission_year is not None and cap_round is not None:
            composite_key = (
                branch_code,
                admission_year,
                cap_round,
                level,
                admission_stage,
                category,
            )
            if composite_key in seen_keys:
                row_errors.append(f"duplicate composite key {composite_key}")
            else:
                seen_keys.add(composite_key)

        if row_errors:
            for reason in row_errors:
                failures.append(ValidationFailure(row_number=idx, reason=reason))
        else:
            valid_count += 1

    return ValidationReport(
        total_rows=len(rows),
        valid_rows=valid_count,
        failures=tuple(failures),
    )


def format_validation_summary(report: ValidationReport, max_errors: int = 20) -> str:
    """Format a human-readable validation summary."""
    lines = [
        "=== ETL Validation Summary ===",
        f"Total rows : {report.total_rows:,}",
        f"Valid rows : {report.valid_rows:,}",
        f"Failures   : {len(report.failures):,}",
    ]
    if report.total_rows == 0:
        lines.append("ERROR: No rows found to validate.")
    elif report.failures:
        lines.append(f"Rejected rows (showing up to {max_errors}):")
        for failure in report.failures[:max_errors]:
            lines.append(f"  - Row {failure.row_number}: {failure.reason}")
        if len(report.failures) > max_errors:
            lines.append(f"  ... and {len(report.failures) - max_errors} more failure(s).")
    else:
        lines.append("Status     : PASSED")
    return "\n".join(lines)


def validate_csv(csv_path: Path) -> ValidationReport:
    """Load *csv_path* with strict string typing, validate, and raise on failure."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    rows = read_csv_strings(csv_path)
    report = validate_rows(rows)
    if not report.is_valid:
        raise ValidationError(report)
    return report
