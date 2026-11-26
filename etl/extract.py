"""Single-pass PDF extraction for MHT-CET CAP cutoff reports."""

from __future__ import annotations

import csv
import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

COLLEGE_RE = re.compile(r"^(\d{5})\s*-\s*(.+)$")
BRANCH_RE = re.compile(r"^(\d{10}[A-Z0-9]*)\s*-\s*(.+)$")
STATUS_RE = re.compile(r"^Status:\s*(.+)$")
STAGE_RE = re.compile(r"^\s*(I{1,3}|IV)\s+\d")
HEADER_RE = re.compile(r"^\s*Stage\s+[A-Z]")
LEGEND_RE = re.compile(r"^Legends:")

LEVEL_LABELS: dict[str, str] = {
    "Other Than Home University Seats Allotted to Other Than Home University Candidates": "OHU_OHU",
    "Other Than Home University Seats Allotted to Home University Candidates": "OHU_HU",
    "Home University Seats Allotted to Other Than Home University Candidates": "HU_OHU",
    "Home University Seats Allotted to Home University Candidates": "HU_HU",
    "State Level": "SL",
}

SKIP_LINES: tuple[str, ...] = (
    "Government of Maharashtra",
    "State Common Entrance Test Cell",
    "Cut Off List for",
    "Degree Courses In",
)

STANDALONE_CATEGORIES: frozenset[str] = frozenset({"TFWS", "EWS", "ORPHAN", "MI", "ALL"})
STRUCTURED_CATEGORY_RE = re.compile(
    r"^(PWDR|DEFR|PWD|DEF|G|L)(SEBC|OPEN|OBC|SC|ST|VJ|NT1|NT2|NT3)(S|H|O)$"
)

DEFAULT_FILENAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?P<year>20\d{2}).*?CAP[_\s-]*(?P<round>\d+)", re.IGNORECASE),
    re.compile(r"(?P<year>20\d{2})[_-]r(?P<round>\d+)", re.IGNORECASE),
)

RAW_CSV_FIELDNAMES: tuple[str, ...] = (
    "college_code",
    "college_name",
    "branch_code",
    "branch_name",
    "status",
    "year",
    "round",
    "level",
    "stage",
    "category",
    "rank",
    "percentile",
)


@dataclass(frozen=True, slots=True)
class PdfSource:
    """Discovered cutoff PDF with its admission year and CAP round."""

    path: Path
    year: int
    round: int


def is_valid_category_code(code: str) -> bool:
    """Return True if *code* is a complete, valid MHT-CET category code."""
    return code in STANDALONE_CATEGORIES or bool(STRUCTURED_CATEGORY_RE.match(code))


def normalize_name(text: str) -> str:
    """Collapse whitespace and normalize spacing around parentheses."""
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"(\w)\(", r"\1 (", normalized)
    normalized = re.sub(r"\(\s+", "(", normalized)
    normalized = re.sub(r"\s+\)", ")", normalized)
    normalized = re.sub(r"\)(\w)", r") \1", normalized)
    return normalized


def extract_pages_from_pdf(pdf_path: Path) -> list[list[str]]:
    """Run ``pdftotext -layout`` once and split output on form-feed characters."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdftotext binary not found. Install Poppler and ensure 'pdftotext' is on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(
            f"pdftotext failed for {pdf_path} with exit code {exc.returncode}: {stderr}"
        ) from exc

    raw_pages = result.stdout.split("\x0c")
    if raw_pages and raw_pages[-1] == "":
        raw_pages.pop()
    return [page.splitlines() for page in raw_pages]


def parse_header_line(line: str) -> list[tuple[int, str]]:
    """Parse category column headers while preserving exact 0-based character positions."""
    tokens = [(m.start(), m.group()) for m in re.finditer(r"\S+", line)]
    if tokens and tokens[0][1] == "Stage":
        return tokens[1:]
    return tokens


def merge_wrapped_header_line(
    categories: list[tuple[int, str]],
    line: str,
    tolerance: int = 15,
) -> list[tuple[int, str]]:
    """Merge wrapped suffix fragments into incomplete category headers (1-to-1 by position)."""
    fragments = [(m.start(), m.group()) for m in re.finditer(r"\S+", line)]
    if not fragments or not categories:
        return categories

    merged = list(categories)
    used_indices: set[int] = set()

    for frag_x, frag_text in fragments:
        best_idx: int | None = None
        best_score: tuple[int, float] | None = None

        for idx, (cat_x, cat_name) in enumerate(merged):
            if idx in used_indices:
                continue
            if is_valid_category_code(cat_name):
                continue

            cat_end = cat_x + len(cat_name)
            if cat_x <= frag_x <= cat_end:
                dist = 0.0
            else:
                dist = float(min(abs(frag_x - cat_x), abs(frag_x - cat_end)))

            if dist > tolerance:
                continue

            # Prefer merges that yield a valid complete category code.
            forms_valid = 0 if is_valid_category_code(cat_name + frag_text) else 1
            score = (forms_valid, dist)
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None:
            cat_x, cat_name = merged[best_idx]
            merged[best_idx] = (cat_x, cat_name + frag_text)
            used_indices.add(best_idx)

    return merged


def parse_value_line(line: str) -> list[tuple[int, str]]:
    """Extract numeric ranks or parenthesized percentiles with their character positions."""
    return [(m.start(), m.group().strip("()")) for m in re.finditer(r"\([\d.]+\)|\d+", line)]


def align(
    categories: list[tuple[int, str]],
    values: list[tuple[int, str]],
    tolerance: int = 18,
) -> dict[str, str]:
    """Align extracted rank/percentile tokens to category header columns."""
    if not categories or not values:
        return {}
    cat0 = categories[0][0]
    val0 = values[0][0]
    result: dict[str, str] = {}
    for cx, name in categories:
        best_val: str | None = None
        best_dist = float("inf")
        for vx, val in values:
            dist = abs((vx - val0) - (cx - cat0))
            if dist < best_dist:
                best_dist = dist
                best_val = val
        if best_val is not None and best_dist <= tolerance:
            result[name] = best_val
    return result


def _is_ignored_line(line: str) -> bool:
    if LEGEND_RE.search(line):
        return True
    if any(skip in line for skip in SKIP_LINES):
        return True
    stripped = line.strip()
    return bool(re.match(r"^\d+$", stripped) or stripped in ("", "D", "i", "r"))


def _matches_level(line: str) -> str | None:
    for full, code in LEVEL_LABELS.items():
        if full in line:
            return code
    return None


def parse_pages(pages: list[list[str]], year: int, round_num: int) -> list[dict[str, object]]:
    """Parse extracted ``pdftotext`` pages into raw cutoff row dicts."""
    rows: list[dict[str, object]] = []

    college_code = college_name = ""
    branch_code = branch_name = ""
    status = level = ""

    state = "waiting_header"
    reading_branch_name = False
    categories: list[tuple[int, str]] = []
    p_stage = ""
    p_ranks: dict[str, str] = {}

    emitted_blocks: set[tuple[str, str, str, frozenset[tuple[str, str]]]] = set()

    for page_lines in pages:
        for raw in page_lines:
            line = raw.rstrip()

            if _is_ignored_line(line):
                continue

            stripped = line.strip()

            # Check structural boundaries before treating a line as branch-name continuation.
            college_match = COLLEGE_RE.match(stripped)
            branch_match = BRANCH_RE.match(stripped)
            status_match = STATUS_RE.match(stripped)
            level_match = _matches_level(line)
            is_header = bool(HEADER_RE.match(line))
            stage_match = STAGE_RE.match(line)

            if reading_branch_name:
                if (
                    college_match
                    or branch_match
                    or status_match
                    or level_match
                    or is_header
                    or stage_match
                ):
                    branch_name = normalize_name(branch_name)
                    reading_branch_name = False
                else:
                    branch_name = f"{branch_name} {stripped}"
                    continue

            if college_match:
                college_code = college_match.group(1)
                college_name = normalize_name(college_match.group(2))
                state = "waiting_header"
                continue

            if branch_match:
                branch_code = branch_match.group(1)
                branch_name = branch_match.group(2).strip()
                reading_branch_name = True
                level = ""
                state = "waiting_header"
                p_stage = ""
                p_ranks = {}
                continue

            if status_match:
                status = normalize_name(status_match.group(1))
                continue

            if level_match:
                level = level_match
                state = "waiting_header"
                categories = []
                p_stage = ""
                p_ranks = {}
                continue

            if is_header:
                categories = parse_header_line(line)
                state = "have_header"
                p_stage = ""
                p_ranks = {}
                continue

            if (
                state == "have_header"
                and stripped
                and not stage_match
                and re.match(r"^\s+[A-Z]", line)
                and not re.search(r"\d", line)
            ):
                categories = merge_wrapped_header_line(categories, line)
                continue

            if stage_match and state == "have_header":
                p_stage = stage_match.group(1).strip()
                p_ranks = align(categories, parse_value_line(line))
                continue

            if p_stage and stripped.startswith("("):
                perc_map = align(categories, parse_value_line(line))
                block_key = (branch_code, level, p_stage, frozenset(p_ranks.items()))
                if block_key not in emitted_blocks:
                    emitted_blocks.add(block_key)
                    for _, cat in categories:
                        rank = p_ranks.get(cat, "")
                        perc = perc_map.get(cat, "")
                        if rank or perc:
                            rows.append(
                                {
                                    "college_code": college_code,
                                    "college_name": college_name,
                                    "branch_code": branch_code,
                                    "branch_name": normalize_name(branch_name),
                                    "status": status,
                                    "year": year,
                                    "round": round_num,
                                    "level": level,
                                    "stage": p_stage,
                                    "category": cat,
                                    "rank": rank,
                                    "percentile": perc,
                                }
                            )
                p_stage = ""
                p_ranks = {}
                continue

    return rows


def discover_pdfs(
    pdf_dir: Path,
    manifest_path: Path | None = None,
    patterns: tuple[re.Pattern[str], ...] = DEFAULT_FILENAME_PATTERNS,
) -> list[PdfSource]:
    """Discover cutoff PDFs in *pdf_dir* via manifest.json or filename regex rules."""
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory does not exist: {pdf_dir}")

    manifest_file = manifest_path or (pdf_dir / "manifest.json")
    if manifest_file.exists():
        raw_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        sources: list[PdfSource] = []
        if isinstance(raw_manifest, dict):
            for filename, meta in raw_manifest.items():
                year, round_num = int(meta[0]), int(meta[1])
                pdf_path = pdf_dir / filename
                if pdf_path.exists():
                    sources.append(PdfSource(path=pdf_path, year=year, round=round_num))
        elif isinstance(raw_manifest, list):
            for entry in raw_manifest:
                pdf_path = pdf_dir / str(entry["filename"])
                if pdf_path.exists():
                    sources.append(
                        PdfSource(
                            path=pdf_path,
                            year=int(entry["year"]),
                            round=int(entry["round"]),
                        )
                    )
        return sorted(sources, key=lambda item: (item.year, item.round, item.path.name))

    sources = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        matched = False
        for pattern in patterns:
            m = pattern.search(pdf_path.stem)
            if m:
                sources.append(
                    PdfSource(
                        path=pdf_path,
                        year=int(m.group("year")),
                        round=int(m.group("round")),
                    )
                )
                matched = True
                break
        if not matched:
            logger.warning("Skipping unrecognized PDF filename: %s", pdf_path.name)

    return sorted(sources, key=lambda item: (item.year, item.round, item.path.name))


def extract_pdf_to_csv(source: PdfSource, output_dir: Path) -> Path:
    """Extract a single PDF into ``<output_dir>/cutoff_<year>_r<round>.csv``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / f"cutoff_{source.year}_r{source.round}.csv"
    pages = extract_pages_from_pdf(source.path)
    rows = parse_pages(pages, year=source.year, round_num=source.round)

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(
        "[%d R%d] Extracted %d rows -> %s",
        source.year,
        source.round,
        len(rows),
        output_csv,
    )
    return output_csv


def extract_all(pdf_dir: Path, output_dir: Path) -> list[Path]:
    """Discover and extract all cutoff PDFs in *pdf_dir* into *output_dir*."""
    sources = discover_pdfs(pdf_dir)
    if not sources:
        raise FileNotFoundError(f"No matching cutoff PDFs found in {pdf_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source in sources:
        outputs.append(extract_pdf_to_csv(source, output_dir))
    return outputs
