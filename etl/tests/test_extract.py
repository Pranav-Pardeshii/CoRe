"""Unit tests for etl.extract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from etl.extract import (
    discover_pdfs,
    extract_pages_from_pdf,
    extract_pdf_to_csv,
    normalize_name,
    parse_pages,
    resolve_pdftotext_cmd,
)


def test_wrapped_header_merging_prevents_double_s_and_truncation() -> None:
    """Wrapped suffix fragments merge 1-to-1 into incomplete codes without corrupting valid ones."""
    page_lines = [
        "06271 - Pune Institute of Computer Technology",
        "0627124510 - Computer Engineering",
        "Status: Un-Aided",
        "State Level",
        "Stage    DEFROBCS   DEFRNT1S   DEFRSEBC   PWDROBC   PWDRSEBC   EWS     ORPHAN",
        "                                  S          S         S",
        "I        1200       3400       4500       5600      6700       890     15000",
        "         (99.10)    (97.50)    (96.80)    (95.20)   (94.10)    (99.40) (88.00)",
    ]

    rows = parse_pages([page_lines], year=2025, round_num=1)
    categories = [str(r["category"]) for r in rows]

    assert categories == [
        "DEFROBCS",
        "DEFRNT1S",
        "DEFRSEBCS",
        "PWDROBCS",
        "PWDRSEBCS",
        "EWS",
        "ORPHAN",
    ]
    for bad in ("DEFROBCSS", "DEFRNT1SS", "EWSS", "ORPHANS", "PWDROBC", "DEFRSEBC", "PWDRSEBC"):
        assert bad not in categories


def test_multiline_branch_name_joining_and_parenthesis_normalization() -> None:
    """Long wrapped branch names are joined cleanly and parenthesis spacing is normalized."""
    assert normalize_name("Engineering(Data Science)") == "Engineering (Data Science)"
    assert (
        normalize_name("Computer Science   ( Data Science )") == "Computer Science (Data Science)"
    )

    page_lines = [
        "06271 - Pune Institute of Computer Technology",
        "0627191210 - Computer Science and Engineering (Internet of Things and Cyber",
        "             Security Including Block Chain Technology)",
        "Status: Un-Aided",
        "Home University Seats Allotted to Home University Candidates",
        "Stage    GOPENS",
        "I        512",
        "         (99.85)",
    ]

    rows = parse_pages([page_lines], year=2026, round_num=1)
    assert len(rows) == 1
    assert rows[0]["branch_name"] == (
        "Computer Science and Engineering (Internet of Things and Cyber "
        "Security Including Block Chain Technology)"
    )


def test_single_pass_pdftotext_splits_on_form_feed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """extract_pages_from_pdf invokes pdftotext once and splits output on \\x0c."""
    pdf_path = tmp_path / "2026_CAP1.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["pdftotext"],
            returncode=0,
            stdout="Page 1 line\x0cPage 2 line\x0c",
            stderr="",
        )
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    pages = extract_pages_from_pdf(pdf_path)
    assert pages == [["Page 1 line"], ["Page 2 line"]]
    mock_run.assert_called_once_with(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def test_extract_pages_handles_non_utf8_bytes_from_pdftotext(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """extract_pages_from_pdf replaces stray non-UTF-8 bytes instead of crashing reader thread."""
    pdf_path = tmp_path / "2026_CAP1.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "pdftotext"
        return real_run(
            [
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'Page 1 \\xb2\\x0cPage 2\\x0c')",
            ],
            **kwargs,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    pages = extract_pages_from_pdf(pdf_path)
    assert pages == [["Page 1 \ufffd"], ["Page 2"]]


def test_extract_pages_raises_clear_runtime_error_when_pdftotext_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing pdftotext binary raises a clear RuntimeError."""
    pdf_path = tmp_path / "2026_CAP1.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    def raise_missing(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("pdftotext")

    monkeypatch.setattr(subprocess, "run", raise_missing)
    with pytest.raises(RuntimeError, match="pdftotext binary not found"):
        extract_pages_from_pdf(pdf_path)


def test_dynamic_pdf_discovery_supports_2026_and_manifest(tmp_path: Path) -> None:
    """discover_pdfs handles 2024-2026+ filenames and optional manifest.json."""
    (tmp_path / "2024ENGG_CAP1_CutOff.pdf").write_bytes(b"")
    (tmp_path / "2025_CAP4.pdf").write_bytes(b"")
    (tmp_path / "2026ENGG_CAP2_CutOff.pdf").write_bytes(b"")
    (tmp_path / "unrelated.pdf").write_bytes(b"")

    discovered = discover_pdfs(tmp_path)
    assert [(s.year, s.round, s.path.name) for s in discovered] == [
        (2024, 1, "2024ENGG_CAP1_CutOff.pdf"),
        (2025, 4, "2025_CAP4.pdf"),
        (2026, 2, "2026ENGG_CAP2_CutOff.pdf"),
    ]


def test_extract_pdf_to_csv_creates_output_dir_and_csv_extension(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """extract_pdf_to_csv auto-creates output_dir and writes .csv files."""
    pdf_path = tmp_path / "pdfs" / "2026_CAP1.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4")
    out_dir = tmp_path / "nested" / "csvs"

    monkeypatch.setattr(
        "etl.extract.extract_pages_from_pdf",
        lambda _path: [
            [
                "06271 - PICT",
                "0627124510 - Computer Engineering",
                "Status: Un-Aided",
                "State Level",
                "Stage    GOPENS",
                "I        100",
                "         (99.90)",
            ]
        ],
    )

    sources = discover_pdfs(pdf_path.parent)
    out_csv = extract_pdf_to_csv(sources[0], out_dir)
    assert out_dir.exists()
    assert out_csv.suffix == ".csv"
    assert out_csv.name == "cutoff_2026_r1.csv"


def test_parse_pages_pads_4_digit_college_and_9_digit_branch_codes() -> None:
    """2022/2023 PDFs with stripped leading zeros (1002 / 100219110) are zero-padded."""
    page_lines = [
        "1002 - Government College of Engineering, Amravati",
        "100219110 - Civil Engineering",
        "Status: Government Autonomous",
        "State Level",
        "Stage    GOPENS",
        "I        40678",
        "         (77.8495773)",
    ]

    rows = parse_pages([page_lines], year=2022, round_num=1)
    assert len(rows) == 1
    assert rows[0]["college_code"] == "01002"
    assert rows[0]["branch_code"] == "0100219110"


def test_resolve_pdftotext_cmd_prefers_poppler_over_xpdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_pdftotext_cmd skips Xpdf (Git for Windows) and selects Poppler."""
    monkeypatch.setattr(
        "etl.extract._find_path_executables",
        lambda _name: [
            r"C:\Program Files\Git\mingw64\bin\pdftotext.exe",
            r"C:\poppler\Library\bin\pdftotext.exe",
        ],
    )

    def fake_run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "Git" in cmd[0]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="pdftotext version 4.00\nCopyright 1996-2017 Glyph & Cog, LLC",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="pdftotext version 26.09.0\nCopyright 2005-2026 The Poppler Developers",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert resolve_pdftotext_cmd() == r"C:\poppler\Library\bin\pdftotext.exe"


def test_resolve_pdftotext_cmd_rejects_xpdf_only_and_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_pdftotext_cmd fails loudly when Poppler is missing or shadowed by Xpdf."""
    monkeypatch.setattr("etl.extract._find_path_executables", lambda _name: [])
    with pytest.raises(RuntimeError, match="pdftotext binary not found"):
        resolve_pdftotext_cmd()

    monkeypatch.setattr(
        "etl.extract._find_path_executables",
        lambda _name: [r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"],
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **_kw: subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="pdftotext version 4.00\nCopyright 1996-2017 Glyph & Cog, LLC",
        ),
    )
    with pytest.raises(RuntimeError, match="non-Poppler pdftotext"):
        resolve_pdftotext_cmd()
