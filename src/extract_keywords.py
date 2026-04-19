"""
Keyword extraction for job descriptions.

Loads a keyword list from keywords.json and searches job text for matches.
Returns matched terms as a comma-separated string for pre-populating notes.
"""

import json
import re
from pathlib import Path

KEYWORDS_PATH = Path(__file__).parent.parent / "data" / "keywords.json"


def load_keywords(path: Path = KEYWORDS_PATH) -> dict[str, list[str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract(text: str, keywords: dict[str, list[str]]) -> str:
    """
    Return a comma-separated string of keyword terms found in text.
    Preserves original casing from keywords.json; matches case-insensitively.
    Terms are deduplicated and ordered by category then term position.
    """
    if not text:
        return ""

    found = []
    seen = set()

    for terms in keywords.values():
        for term in terms:
            if term.lower() in seen:
                continue
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                found.append(term)
                seen.add(term.lower())

    return ", ".join(found)


if __name__ == "__main__":
    # Quick test: print keywords found in each saved job
    import csv
    import sys

    csv_path = Path(__file__).parent.parent / "data" / "jobs.csv"
    if not csv_path.exists():
        sys.exit("jobs.csv not found.")

    kw = load_keywords()
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = row["job_description"] + " " + row["requirements"]
            found = extract(text, kw)
            print(f"{row['title'][:60]:<60}  {found}")
