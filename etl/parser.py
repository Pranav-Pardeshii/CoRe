import re
import csv
import subprocess
from pathlib import Path


ROUND_RE   = re.compile(r'^Round\s*(.+)$')
COLLEGE_RE = re.compile(r'^(\d{5})\s*-\s*(.+)$')
BRANCH_RE  = re.compile(r'^(\d{10}[A-Z0-9]*)\s*-\s*(.+)$')
STATUS_RE  = re.compile(r'^Status:\s*(.+)$')
STAGE_RE   = re.compile(r'^\s*(I{1,3}|IV)\s+\d')
HEADER_RE  = re.compile(r'^\s*Stage\s+[A-Z]')
LEGEND_RE  = re.compile(r'^Legends:')

LEVEL_LABELS = {
    "Other Than Home University Seats Allotted to Other Than Home University Candidates": "OHU_OHU",
    "Other Than Home University Seats Allotted to Home University Candidates":            "OHU_HU",
    "Home University Seats Allotted to Other Than Home University Candidates":            "HU_OHU",
    "Home University Seats Allotted to Home University Candidates":                       "HU_HU",
    "State Level":                                                                        "SL",
}

SKIP_LINES = [
    "Government of Maharashtra",
    "State Common Entrance Test Cell",
    "Cut Off List for",
    "Degree Courses In",
]

def get_page_count(pdf_path):
    result = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    return 0

def extract_text_per_page(pdf_path, total_pages):
    pages = []
    for p in range(1, total_pages + 1):
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf_path, "-"],
            capture_output=True, text=True
        )
        pages.append(result.stdout.splitlines())
    return pages

def parse_header_line(line):
    stripped = re.sub(r'^\s*Stage\s+', '', line)
    return [(m.start(), m.group()) for m in re.finditer(r'\S+', stripped)]

def parse_value_line(line):
    return [(m.start(), m.group().strip('()'))
            for m in re.finditer(r'\([\d.]+\)|\d+', line)]

def align(categories, values, tolerance=18):
    if not categories or not values:
        return {}
    cat0 = categories[0][0]
    val0 = values[0][0]
    result = {}
    for cx, name in categories:
        best_val, best_dist = None, float('inf')
        for vx, val in values:
            d = abs((vx - val0) - (cx - cat0))
            if d < best_dist:
                best_dist, best_val = d, val
        if best_val is not None and best_dist <= tolerance:
            result[name] = best_val
    return result

def parse_pages(pages, YEAR, ROUND):
    rows = []

    college_code = college_name = ""
    branch_code  = branch_name  = ""
    status       = level        = ""

    state      = "waiting_header"
    categories = []
    p_stage    = ""
    p_ranks    = {}

    # Track emitted blocks globally to handle page-break duplicates
    emitted_blocks = set()

    for page_lines in pages:
        for raw in page_lines:
            line = raw.rstrip()

            if LEGEND_RE.search(line):
                continue
            if any(s in line for s in SKIP_LINES):
                continue
            if re.match(r'^\s*\d+\s*$', line) or line.strip() in ('', 'D', 'i', 'r'):
                continue

            # College
            m = COLLEGE_RE.match(line.strip())
            if m:
                college_code = m.group(1)
                college_name = m.group(2).strip()
                state = "waiting_header"
                continue

            # Branch — reset emitted_blocks when branch changes
            m = BRANCH_RE.match(line.strip())
            if m:
                branch_code = m.group(1)
                branch_name = m.group(2).strip()
                level  = ""
                state  = "waiting_header"
                p_stage = ""
                p_ranks = {}
                continue

            # Status
            m = STATUS_RE.match(line.strip())
            if m:
                status = m.group(1).strip()
                continue

            # Level label
            matched_level = False
            for full, code in LEVEL_LABELS.items():
                if full in line:
                    level      = code
                    state      = "waiting_header"
                    categories = []
                    p_stage    = ""
                    p_ranks    = {}
                    matched_level = True
                    break
            if matched_level:
                continue

            # Column header row
            if HEADER_RE.match(line):
                categories = parse_header_line(line)
                state      = "have_header"
                p_stage    = ""
                p_ranks    = {}
                continue

            # Wrapped header suffix line (e.g. "                    S               S")
            # These are suffix fragments for category names that wrapped to next line.
            # Merge each fragment into the nearest preceding category name.
            if state == "have_header" and line.strip() and not STAGE_RE.match(line):
                if re.match(r'^\s+[A-Z]', line) and not re.search(r'\d', line):
                    extra = [(m.start(), m.group()) for m in re.finditer(r'\S+', line)]
                    new_cats = []
                    for cx, name in categories:
                        best_suffix, best_dist = None, float('inf')
                        for ex, efrag in extra:
                            d = abs(ex - cx)
                            if d < best_dist:
                                best_dist, best_suffix = d, efrag
                        if best_suffix and best_dist <= 20:
                            new_cats.append((cx, name + best_suffix))
                        else:
                            new_cats.append((cx, name))
                    categories = new_cats
                    continue

            # Stage row (rank values)
            m = STAGE_RE.match(line)
            if m and state == "have_header":
                p_stage = m.group(1).strip()
                p_ranks = align(categories, parse_value_line(line))
                continue

            # Percentile row
            if p_stage and line.strip().startswith('('):
                perc_map = align(categories, parse_value_line(line))

                # Deduplicate: skip if this exact block was already emitted
                # (handles Crystal Reports page-break repeats)
                block_key = (branch_code, level, p_stage,
                             frozenset(p_ranks.items()))
                if block_key not in emitted_blocks:
                    emitted_blocks.add(block_key)
                    for _, cat in categories:
                        rank = p_ranks.get(cat, "")
                        perc = perc_map.get(cat, "")
                        if rank or perc:
                            rows.append({
                                "college_code": college_code,
                                "college_name": college_name,
                                "branch_code":  branch_code,
                                "branch_name":  branch_name,
                                "status":       status,
                                "year":         YEAR,
                                "round":        ROUND,
                                "level":        level,
                                "stage":        p_stage,
                                "category":     cat,
                                "rank":         rank,
                                "percentile":   perc,
                            })

                p_stage = ""
                p_ranks = {}
                continue

    return rows

def main(PDF_PATH, YEAR, ROUND):
    OUTPUT_CSV = Path(__file__).parent.parent / "csvs" / f"cutoff_{YEAR}_r{ROUND}.csv"
    
    total = get_page_count(PDF_PATH)
    print(f"\n[{YEAR} R{ROUND}] Total pages: {total}")

    print(f"Extracting text from all {total} pages...")
    pages = extract_text_per_page(PDF_PATH, total)

    print("Parsing...")
    rows = parse_pages(pages, YEAR, ROUND)
    print(f"Extracted {len(rows):,} rows")

    Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["college_code","college_name","branch_code","branch_name",
                  "status","year","round","level","stage","category","rank","percentile"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved → {OUTPUT_CSV}")

    from collections import Counter
    keys  = [(r['branch_code'], r['level'], r['stage'], r['category']) for r in rows]
    dupes = [(k, v) for k, v in Counter(keys).items() if v > 1]
    print(f"Duplicate key check: {len(dupes)} dupes")
    print(f"Colleges : {len({r['college_code'] for r in rows})}")
    print(f"Branches : {len({r['branch_code']  for r in rows})}")

if __name__ == "__main__":
    main(
        PDF_PATH = Path(__file__).parent.parent / "PDFs" / "2025_CAP1.pdf",
        YEAR     = 2025,
        ROUND    = 1
    )