import csv
import mysql.connector
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "your-railway-host",
    "port":     3306,
    "user":     "your-user",
    "password": "your-password",
    "database": "your-database",
    "use_pure": True,
}

FLAT_CSV = "cutoffs_flat.csv"

# ── Read flat CSV ─────────────────────────────────────────────────────────────
print("Reading CSV...")
with open(FLAT_CSV, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print(f"  {len(rows):,} rows loaded")

# ── Deduplicate into 3 tables ─────────────────────────────────────────────────

# colleges — unique by college_code
colleges = {}
for r in rows:
    code = r["college_code"]
    if code not in colleges:
        colleges[code] = (
            r["college_code"],
            r["college_name"],
            r["status"],
        )

# branches — unique by branch_code
branches = {}
for r in rows:
    code = r["branch_code"]
    if code not in branches:
        branches[code] = (
            r["branch_code"],
            r["branch_name"],
            r["college_code"],
        )

# cutoffs — every row
cutoffs = [
    (
        r["branch_code"],
        int(r["year"]),
        int(r["round"]),
        r["level"],
        r["stage"],
        r["category"],
        int(r["rank"]),
        float(r["percentile"]),
    )
    for r in rows
]

print(f"  {len(colleges)} colleges")
print(f"  {len(branches)} branches")
print(f"  {len(cutoffs):,} cutoff rows")

# ── Connect ───────────────────────────────────────────────────────────────────
print("\nConnecting to database...")
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()
print("  Connected.")

# ── Create tables ─────────────────────────────────────────────────────────────
print("\nCreating tables...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS colleges (
        college_code  VARCHAR(10)  PRIMARY KEY,
        college_name  VARCHAR(300) NOT NULL,
        status        VARCHAR(300),
        district      VARCHAR(100)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        branch_code   VARCHAR(15)  PRIMARY KEY,
        branch_name   VARCHAR(300) NOT NULL,
        college_code  VARCHAR(10)  NOT NULL,
        FOREIGN KEY (college_code) REFERENCES colleges(college_code)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS cutoffs (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        branch_code   VARCHAR(15)  NOT NULL,
        year          SMALLINT     NOT NULL,
        round         TINYINT      NOT NULL,
        level         VARCHAR(10)  NOT NULL,
        stage         VARCHAR(5)   NOT NULL,
        category      VARCHAR(20)  NOT NULL,
        rank          INT          NOT NULL,
        percentile    FLOAT        NOT NULL,
        FOREIGN KEY (branch_code) REFERENCES branches(branch_code),
        UNIQUE KEY unique_cutoff (branch_code, year, round, level, stage, category)
    )
""")

db.commit()
print("  Tables ready.")

# ── Insert ────────────────────────────────────────────────────────────────────
print("\nInserting colleges...")
cursor.executemany("""
    INSERT IGNORE INTO colleges (college_code, college_name, status)
    VALUES (%s, %s, %s)
""", list(colleges.values()))
db.commit()
print(f"  {cursor.rowcount} rows inserted")

print("Inserting branches...")
cursor.executemany("""
    INSERT IGNORE INTO branches (branch_code, branch_name, college_code)
    VALUES (%s, %s, %s)
""", list(branches.values()))
db.commit()
print(f"  {cursor.rowcount} rows inserted")

print("Inserting cutoffs...")
cursor.executemany("""
    INSERT IGNORE INTO cutoffs
        (branch_code, year, round, level, stage, category, rank, percentile)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
""", cutoffs)
db.commit()
print(f"  {cursor.rowcount} rows inserted")

# ── Verify ────────────────────────────────────────────────────────────────────
print("\nVerifying...")
cursor.execute("SELECT COUNT(*) FROM colleges")
print(f"  colleges : {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM branches")
print(f"  branches : {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM cutoffs")
print(f"  cutoffs  : {cursor.fetchone()[0]}")

cursor.close()
db.close()
print("\nDone.")