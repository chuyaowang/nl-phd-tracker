#!/usr/bin/env python3
"""
Fetch all saved (favourited) PhD jobs from AcademicTransfer via the API.

Usage:
    python fetch_saved_jobs.py              # reads token from .env
    python fetch_saved_jobs.py --token "Bearer <your_token>"
    python fetch_saved_jobs.py -o jobs.csv  # custom output file
"""

import argparse
import csv
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from extract_keywords import extract, load_keywords

_KEYWORDS = load_keywords()


def load_token_from_env(env_path: Path) -> str:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("AT_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""

OUTPUT_FIELDS = [
    "url", "job_id", "title", "institution", "city", "country",
    "deadline", "date_posted", "salary_min_eur", "salary_max_eur",
    "weekly_hours", "contract_duration",
    "job_description", "requirements", "conditions_of_employment",
    "employer", "department", "contact_name", "contact_email",
    "type", "fit", "application_status", "keywords", "notes",
]

API_BASE = "https://api.academictransfer.com/careers/vacancies/"
API_PARAMS = {
    "boost_spotlights": "false",
    "is_active": "all",
    "is_favorite": "true",
    "limit": 100,
    "offset": 0,
    "ordering": "-start_date",
    "smcv": "false",
    "smrp": "false",
}


def strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(separator="\n", strip=True)


def fmt_date(iso: str) -> str:
    if not iso:
        return ""
    return iso[:10]  # YYYY-MM-DD


def extract_contact(html: str) -> tuple[str, str]:
    if not html:
        return "", ""
    soup = BeautifulSoup(html, "lxml")
    mailto = soup.find("a", href=lambda h: h and h.startswith("mailto:"))
    if not mailto:
        return "", ""
    email = mailto["href"].replace("mailto:", "").strip()
    name = ""
    for prev in mailto.previous_siblings:
        t = prev.get_text(strip=True) if hasattr(prev, "get_text") else str(prev).strip()
        if t and t not in ("📧", ""):
            name = t
            break
    return name, email


def fetch_all(token: str) -> list[dict]:
    headers = {"Authorization": token, "Accept": "application/json"}
    results = []
    params = dict(API_PARAMS)

    while True:
        r = requests.get(API_BASE, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("next"):
            break
        params["offset"] += params["limit"]

    return results


def parse_item(item: dict) -> dict:
    t = next((x for x in item.get("translations", []) if x.get("language_code") == "en"),
             item.get("translations", [{}])[0] if item.get("translations") else {})

    contact_name, contact_email = extract_contact(t.get("additional_info", ""))

    hours_min = item.get("min_weekly_hours", "")
    hours_max = item.get("max_weekly_hours", "")
    weekly_hours = (f"{int(hours_min)}–{int(hours_max)} h/wk" if hours_min != hours_max
                    else f"{int(hours_min)} h/wk" if hours_min else "")

    return {
        "url":                      item.get("absolute_url", ""),
        "job_id":                   item.get("external_id", ""),
        "title":                    t.get("title", ""),
        "institution":              t.get("organisation_name", ""),
        "city":                     item.get("city", ""),
        "country":                  item.get("country_code", ""),
        "deadline":                 fmt_date(item.get("end_date", "")),
        "date_posted":              fmt_date(item.get("start_date", "")),
        "salary_min_eur":           item.get("min_salary", ""),
        "salary_max_eur":           item.get("max_salary", ""),
        "weekly_hours":             weekly_hours,
        "contract_duration":        t.get("contract_duration", ""),
        "job_description":          strip_html(t.get("description", "")),
        "requirements":             strip_html(t.get("requirements", "")),
        "conditions_of_employment": strip_html(t.get("contract_terms", "")),
        "employer":                 strip_html(t.get("organisation_description", "")),
        "department":               strip_html(t.get("department_description", "")),
        "contact_name":             contact_name,
        "contact_email":            contact_email,
        "type":                     "",
        "fit":                      "",
        "application_status":       "not started",
        "keywords":                 extract(
            strip_html(t.get("description", "")) + " " + strip_html(t.get("requirements", "")),
            _KEYWORDS
        ),
        "notes":                    "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default="", help='Authorization header value, e.g. "Bearer <token>". Falls back to AT_TOKEN in .env.')
    parser.add_argument("-o", "--output",
                        default=str(Path(__file__).parent.parent / "data" / "jobs.csv"))
    args = parser.parse_args()

    token = args.token or load_token_from_env(Path(__file__).parent.parent / ".env")
    if not token:
        raise SystemExit("No token found. Set AT_TOKEN in .env or pass --token.")

    print("Fetching saved jobs from API...")
    items = fetch_all(token)
    print(f"Found {len(items)} saved jobs. Parsing...")

    new_rows = {str(r["job_id"]): r for r in (parse_item(i) for i in items)}

    # Preserve manual edits for existing jobs, merge new jobs with defaults
    MANUAL_FIELDS = ["type", "fit", "application_status", "notes"]
    output_path = Path(args.output)
    if output_path.exists():
        import csv as _csv
        with open(output_path, newline="", encoding="utf-8") as f:
            existing = {row["job_id"]: row for row in _csv.DictReader(f)}
        preserved, added = 0, 0
        for job_id, row in new_rows.items():
            if job_id in existing:
                for field in MANUAL_FIELDS:
                    row[field] = existing[job_id].get(field, "")
                preserved += 1
            else:
                added += 1
        print(f"  {preserved} existing jobs (manual edits kept), {added} new jobs added.")
    else:
        print(f"  No existing file — writing {len(new_rows)} jobs fresh.")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(new_rows.values())

    print(f"Done. {len(new_rows)} jobs saved to {output_path}")


if __name__ == "__main__":
    main()
