import csv
from pathlib import Path

csvs_dir = Path(__file__).parent.parent / "csvs"
output   = Path(__file__).parent.parent / "cutoffs_flat.csv"

all_rows = []
fieldnames = None

for f in sorted(csvs_dir.glob("cutoff_*.csv")):  # note: add .csv extension to your output files
    with open(f, newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        if fieldnames is None:
            fieldnames = reader.fieldnames
        for row in reader:
            all_rows.append(row)
    print(f"  {f.name}: {len(all_rows):,} rows so far")

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\nMerged {len(all_rows):,} rows → {output}")
