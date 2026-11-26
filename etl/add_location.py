from pathlib import Path

import pandas as pd

PREFIX_TO_DIVISION = {
    "01": "Amravati Division",
    "02": "Aurangabad Division",
    "03": "Mumbai Division",
    "04": "Nagpur Division",
    "05": "Nashik Division",
    "06": "Pune Division",
    "14": "Nagpur Division",
    "16": "Pune Division",
}

FLAT_CSV_PATH = Path(__file__).resolve().parents[1] / "cutoffs_flat.csv"


def add_division_column(csv_path: Path = FLAT_CSV_PATH) -> None:
    """Populate the division column from the 2-digit college code prefix."""
    cutoffs_df = pd.read_csv(csv_path)
    cutoffs_df["division"] = (
        cutoffs_df["college_code"]
        .astype(str)
        .str.zfill(5)
        .str[:2]
        .map(PREFIX_TO_DIVISION)
        .fillna("")
    )
    cutoffs_df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    add_division_column()
