import csv
from pathlib import Path

# District lookup by 3-digit college code prefix
# Based on DTE Maharashtra's regional coding + college name verification
PREFIX_TO_DISTRICT = {
    # Amravati Division
    "010": "Amravati",
    "011": "Amravati",
    "012": "Buldhana",

    # Aurangabad / Marathwada Division
    "020": "Chhatrapati Sambhajinagar",
    "021": "Chhatrapati Sambhajinagar",
    "022": "Parbhani",
    "025": "Nanded",
    "026": "Nanded",
    "027": "Beed",

    # Mumbai / Konkan Division
    "030": "Mumbai",
    "031": "Mumbai",
    "032": "Mumbai",
    "033": "Raigad",
    "034": "Thane",
    "035": "Thane",
    "037": "Thane",

    # Nagpur Division
    "040": "Nagpur",
    "041": "Nagpur",
    "043": "Nagpur",
    "046": "Wardha",
    "047": "Chandrapur",

    # Nashik / North Maharashtra Division
    "050": "Jalgaon",
    "051": "Jalgaon",
    "052": "Jalgaon",
    "053": "Ahmednagar",
    "054": "Nashik",
    "055": "Nashik",

    # Pune Division
    "060": "Pune",
    "061": "Pune",
    "062": "Pune",
    "063": "Satara",
    "064": "Kolhapur",
    "065": "Satara",
    "066": "Pune",
    "067": "Kolhapur",
    "068": "Kolhapur",
    "069": "Solapur",

    # Autonomous / Special Universities
    "140": "Nagpur",
    "160": "Pune",
    "161": "Kolhapur",
    "163": "Pune",
}

# College-level overrides for cases where prefix alone is ambiguous
COLLEGE_OVERRIDES = {
    "03033": "Raigad",    # DBATU Lonere is Raigad, not Mumbai
    "03042": "Ratnagiri", # Loknete Shamrao Peje GCE is Ratnagiri
}

def add_district(colleges_csv, out_csv):
    colleges = list(csv.DictReader(open(colleges_csv)))
    unknown = []

    for c in colleges:
        prefix = c["college_code"][:3]
        district = COLLEGE_OVERRIDES.get(c["college_code"],
                    PREFIX_TO_DISTRICT.get(prefix, ""))
        c["district"] = district
        if not district:
            unknown.append((c["college_code"], c["college_name"]))

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["college_code","college_name","status","district"])
        writer.writeheader()
        writer.writerows(colleges)

    print(f"Written {len(colleges)} colleges to {out_csv}")
    if unknown:
        print(f"\n{len(unknown)} colleges with unknown district:")
        for code, name in unknown:
            print(f"  {code} | {name}")
    else:
        print("All colleges have a district assigned.")

add_district(
    "/mnt/user-data/outputs/colleges.csv",
    "/mnt/user-data/outputs/colleges.csv"
)