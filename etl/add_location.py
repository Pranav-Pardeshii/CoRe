import pandas as pd
from pathlib import Path

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

df = pd.read_csv("cutoffs_flat.csv")

df["division"] = df["college_code"].astype(str).str.zfill(5).str[:2].map(PREFIX_TO_DIVISION).fillna("")

df.to_csv("cutoffs_flat.csv", index=False)

print(df["division"].value_counts())