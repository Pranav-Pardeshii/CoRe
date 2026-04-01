from parser import parse_pages, extract_text_per_page, get_page_count
from pathlib import Path
import csv

FILES = {
    "2024ENGG_CAP1_CutOff.pdf": (2024, 1),
    "2024ENGG_CAP2_CutOff.pdf": (2024, 2),
    "2024ENGG_CAP3_CutOff.pdf": (2024, 3),
    "2025_CAP1.pdf":             (2025, 1),
    "2025_CAP2.pdf":             (2025, 2),
    "2025_CAP3.pdf":             (2025, 3),
    "2025_CAP4.pdf":             (2025, 4),
}


PDF_DIR = Path(__file__).parent.parent / "PDFs"

for filename, (year, round_) in FILES.items():
    pdf = PDF_DIR / filename
    if not pdf.exists():
        print(f"SKIP: {filename}")
        continue
    
    print(f"\nProcessing {filename}...")
    total = get_page_count(str(pdf))
    pages = extract_text_per_page(str(pdf), total)
    rows  = parse_pages(pages, year, round_)  # pass year+round in
    
    # save to CSV
    output = Path(__file__).parent.parent / "csvs" / f"cutoff_{year}_r{round_}"
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows):,} rows → {output}")