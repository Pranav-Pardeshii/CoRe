"""Unit tests for etl.config, etl.load, and etl.cli."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from etl.cli import main as cli_main
from etl.config import DatabaseConfig, load_db_config
from etl.load import UPSERT_CUTOFFS_SQL, load_csv_to_db, prepare_records
from etl.transform import write_flat_csv


def _make_rows(count: int) -> list[dict[str, str]]:
    return [
        {
            "college_code": "06271",
            "college_name": "PICT",
            "branch_code": "0627124510",
            "branch_name": "Computer Engineering",
            "status": "Un-Aided",
            "division": "Pune Division",
            "year": "2025",
            "round": str(idx + 1),
            "level": "SL",
            "stage": "I",
            "category": "GOPENS",
            "rank": str(100 + idx),
            "percentile": "99.50",
        }
        for idx in range(count)
    ]


def test_config_supports_legacy_env_and_resolves_ssl_ca(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """load_db_config falls back to DB_* and resolves relative DB_SSL_CA against repo root."""
    for key in (
        "CORE_DB_USER",
        "CORE_DB_PASS",
        "CORE_DB_NAME",
        "CORE_DB_HOST",
        "CORE_DB_PORT",
        "CORE_DB_UNIX_SOCKET",
        "CORE_DB_SSL_CA",
    ):
        monkeypatch.delenv(key, raising=False)

    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("CERT", encoding="utf-8")

    monkeypatch.setenv("DB_USER", "legacy_user")
    monkeypatch.setenv("DB_PASS", "secret")
    monkeypatch.setenv("DB_NAME", "core_db")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_SSL_CA", "./ca.pem")

    cfg = load_db_config(env_file=None, repo_root=tmp_path)
    kwargs = cfg.to_connector_kwargs()
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 3307
    assert kwargs["ssl_ca"] == str(ca_file.resolve())
    assert kwargs["ssl_verify_cert"] is True


def test_config_supports_unix_socket(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """load_db_config supports Cloud SQL unix_socket without requiring DB_HOST."""
    for key in ("CORE_DB_HOST", "DB_HOST", "CORE_DB_SSL_CA", "DB_SSL_CA"):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("CORE_DB_USER", "cloud_user")
    monkeypatch.setenv("CORE_DB_PASS", "pw")
    monkeypatch.setenv("CORE_DB_NAME", "core_db")
    monkeypatch.setenv("CORE_DB_UNIX_SOCKET", "/cloudsql/proj:region:inst")

    cfg = load_db_config(env_file=None, repo_root=tmp_path)
    kwargs = cfg.to_connector_kwargs()
    assert kwargs["unix_socket"] == "/cloudsql/proj:region:inst"
    assert "host" not in kwargs


def test_load_chunks_executemany_and_logs_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """load_csv_to_db upserts in batches and checks post-load table counts."""
    csv_path = tmp_path / "cutoffs.csv"
    write_flat_csv(_make_rows(5), csv_path)

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("alembic_version",),
        ("colleges",),
        ("branches",),
        ("admission_cutoffs",),
    ]
    mock_cursor.fetchone.side_effect = [(1,), (1,), (5,)]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    monkeypatch.setattr("etl.load.mysql.connector.connect", lambda **_kw: mock_conn)

    cfg = DatabaseConfig(user="u", password="p", database="core", host="127.0.0.1")
    counts = load_csv_to_db(csv_path, db_config=cfg, batch_size=2)

    assert counts == {"colleges": 1, "branches": 1, "admission_cutoffs": 5}
    cutoff_calls = [
        call
        for call in mock_cursor.executemany.call_args_list
        if call.args[0] == UPSERT_CUTOFFS_SQL
    ]
    assert [len(call.args[1]) for call in cutoff_calls] == [2, 2, 1]
    assert mock_conn.commit.call_count == 5  # 1 colleges + 1 branches + 3 cutoffs
    assert "AS new" in UPSERT_CUTOFFS_SQL


def test_prepare_records_preserves_decimal_precision() -> None:
    """prepare_records keeps 7-decimal percentiles as Decimal without float drift."""
    rows = _make_rows(1)
    rows[0]["percentile"] = "99.1234567"
    _colleges, _branches, cutoffs = prepare_records(rows)
    assert isinstance(cutoffs[0][7], Decimal)
    assert cutoffs[0][7] == Decimal("99.1234567")


def test_load_fails_on_missing_alembic_tables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """load_csv_to_db aborts if Alembic-managed tables are missing."""
    csv_path = tmp_path / "cutoffs.csv"
    write_flat_csv(_make_rows(1), csv_path)

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("colleges",)]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr("etl.load.mysql.connector.connect", lambda **_kw: mock_conn)

    cfg = DatabaseConfig(user="u", password="p", database="core", host="127.0.0.1")
    with pytest.raises(RuntimeError, match="alembic_version"):
        load_csv_to_db(csv_path, db_config=cfg)


def test_cli_validate_and_dry_run_load(tmp_path: Path) -> None:
    """CLI validate and load --dry-run return 0 on valid CSV and 1 on invalid CSV."""
    csv_path = tmp_path / "valid.csv"
    write_flat_csv(_make_rows(2), csv_path)

    assert cli_main(["validate", "--csv-path", str(csv_path)]) == 0
    assert cli_main(["load", "--csv-path", str(csv_path), "--dry-run"]) == 0

    bad_csv = tmp_path / "bad.csv"
    bad_rows = _make_rows(1)
    bad_rows[0]["category"] = "EWSS"
    write_flat_csv(bad_rows, bad_csv)
    assert cli_main(["validate", "--csv-path", str(bad_csv)]) == 1
