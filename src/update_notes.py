"""Overwrite notes for all jobs with freshly extracted keywords."""

import csv
from pathlib import Path
from extract_keywords import extract, load_keywords

CSV_PATH = Path(__file__).parent.parent / "data" / "jobs.csv"

keywords = load_keywords()
rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))

for row in rows:
    text = row["job_description"] + " " + row["requirements"]
    row["notes"] = extract(text, keywords)

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Updated notes for all {len(rows)} jobs.")
