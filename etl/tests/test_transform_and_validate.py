"""Unit tests for etl.transform and etl.validate."""

from __future__ import annotations

from pathlib import Path

import pytest
from etl.transform import read_csv_strings, transform_rows, write_flat_csv
from etl.validate import ValidationError, validate_csv, validate_rows


def _sample_row(**overrides: str) -> dict[str, str]:
    base = {
        "college_code": "06271",
        "college_name": "Pune Institute of Computer Technology",
        "branch_code": "0627124510",
        "branch_name": "Computer Engineering",
        "status": "Un-Aided",
        "division": "Pune Division",
        "year": "2025",
        "round": "1",
        "level": "SL",
        "stage": "I",
        "category": "GOPENS",
        "rank": "512",
        "percentile": "99.85",
    }
    base.update(overrides)
    return base


def test_leading_zero_preservation_through_transform_and_csv_roundtrip(tmp_path: Path) -> None:
    """Leading zeros in college_code (06271) and branch_code (0627124510) survive roundtrip."""
    raw = [_sample_row(college_code="6271", branch_code="0627124510")]
    transformed = transform_rows(raw)
    assert transformed[0]["college_code"] == "06271"
    assert transformed[0]["branch_code"] == "0627124510"
    assert transformed[0]["division"] == "Pune Division"

    csv_path = tmp_path / "cutoffs_flat.csv"
    write_flat_csv(transformed, csv_path)
    reloaded = read_csv_strings(csv_path)

    assert reloaded[0]["college_code"] == "06271"
    assert reloaded[0]["branch_code"] == "0627124510"
    assert reloaded[0]["rank"] == "512"
    report = validate_csv(csv_path)
    assert report.is_valid


def test_unmapped_division_prefix_raises_loudly() -> None:
    """Unmapped 2-digit college_code prefix fails loudly instead of writing empty string."""
    raw = [_sample_row(college_code="99123", branch_code="9912324510")]
    with pytest.raises(ValueError, match="99"):
        transform_rows(raw)


def test_transform_deduplicates_composite_key() -> None:
    """Duplicate composite keys are deduplicated during transform."""
    raw = [_sample_row(rank="512"), _sample_row(rank="999")]
    transformed = transform_rows(raw)
    assert len(transformed) == 1
    assert transformed[0]["rank"] == "512"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("percentile", "-0.01"),
        ("percentile", "100.01"),
        ("percentile", "NaN"),
        ("rank", "0"),
        ("rank", "-10"),
        ("rank", "512.0"),
        ("category", "DEFROBCSS"),
        ("category", "EWSS"),
        ("category", "ORPHANS"),
        ("category", "PWDROBC"),
        ("category", "DEFRSEBC"),
        ("college_code", "6271"),
        ("branch_code", "0300124510"),
        ("level", "INVALID"),
        ("division", ""),
        ("year", "2019"),
        ("round", "11"),
    ],
)
def test_validator_rejects_invalid_fields(field: str, value: str) -> None:
    """validate_rows rejects out-of-range percentiles, invalid ranks, and corrupted categories."""
    row = _sample_row(**{field: value})
    report = validate_rows([row])
    assert not report.is_valid
    assert len(report.failures) >= 1


def test_validator_rejects_duplicate_composite_keys(tmp_path: Path) -> None:
    """validate_csv aborts with ValidationError when duplicate composite keys exist."""
    csv_path = tmp_path / "dupes.csv"
    write_flat_csv([_sample_row(), _sample_row(rank="600")], csv_path)
    with pytest.raises(ValidationError, match="duplicate composite key"):
        validate_csv(csv_path)
