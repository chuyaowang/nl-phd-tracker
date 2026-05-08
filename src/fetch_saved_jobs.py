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
import re
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

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
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not href.startswith("mailto:"):
            a.replace_with(f"[{text}]({href})" if text else href)
    text = soup.get_text(separator="\n", strip=True)
    # get_text inserts \n around replaced link strings even when they're inline.
    # Remove those newlines when non-whitespace text sits on both sides.
    text = re.sub(r"(?<=\S)\n(\[[^\]\n]+\]\([^)\n]+\))", r" \1", text)
    text = re.sub(r"(\[[^\]\n]+\]\([^)\n]+\))\n(?=\S)", r"\1 ", text)
    return text


_SECTION_HEADERS = [
    (re.compile(r"job\s+description", re.I),             "job_description"),
    (re.compile(r"job\s+requirements?", re.I),            "requirements"),
    (re.compile(r"conditions?\s+of\s+employment", re.I),  "conditions_of_employment"),
]


def _split_description(html: str) -> dict[str, str]:
    """Split a flat description HTML into sections by <strong> header tags.
    Only called when the API's dedicated section fields are empty."""
    soup = BeautifulSoup(html, "lxml")

    header_tags: list[tuple] = []
    for strong in soup.find_all("strong"):
        label = strong.get_text(strip=True)
        for pattern, field in _SECTION_HEADERS:
            if pattern.search(label):
                header_tags.append((strong, field))
                break

    if not header_tags:
        return {}

    result = {}
    for i, (strong_tag, field) in enumerate(header_tags):
        next_strong = header_tags[i + 1][0] if i + 1 < len(header_tags) else None
        chunks = []
        node = strong_tag.next_sibling
        while node is not None:
            if node is next_strong:
                break
            if next_strong and isinstance(node, Tag) and node.find(lambda t: t is next_strong):
                break
            chunks.append(str(node))
            node = node.next_sibling
        content = "".join(chunks).strip()
        if content:
            result[field] = content

    return result


def fmt_date(iso: str) -> str:
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso)
    # T00:00:00 means "expired at midnight" — the deadline was the previous day
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        dt -= timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


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
    url: str | None = API_BASE
    params: dict | None = dict(API_PARAMS)

    while url:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")
        params = None  # next URL already has all query params encoded

    return results


def parse_item(item: dict) -> dict:
    t = next((x for x in item.get("translations", []) if x.get("language_code") == "en"),
             item.get("translations", [{}])[0] if item.get("translations") else {})

    contact_name, contact_email = extract_contact(t.get("additional_info", ""))

    hours_min = item.get("min_weekly_hours", "")
    hours_max = item.get("max_weekly_hours", "")
    weekly_hours = (f"{int(hours_min)}–{int(hours_max)} h/wk" if hours_min != hours_max
                    else f"{int(hours_min)} h/wk" if hours_min else "")

    # When the API's dedicated fields are empty, try to split the description HTML
    # by known <strong> section headers to populate them.
    flat = not t.get("requirements") and not t.get("contract_terms")
    sections = _split_description(t.get("description", "")) if flat else {}

    desc_html   = sections.get("job_description") or t.get("description", "")
    req_html    = sections.get("requirements")     or t.get("requirements", "")
    cond_html   = sections.get("conditions_of_employment") or t.get("contract_terms", "")

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
        "job_description":          strip_html(desc_html),
        "requirements":             strip_html(req_html),
        "conditions_of_employment": strip_html(cond_html),
        "employer":                 strip_html(t.get("organisation_description", "")),
        "department":               strip_html(t.get("department_description", "")),
        "contact_name":             contact_name,
        "contact_email":            contact_email,
        "type":                     "",
        "fit":                      "",
        "application_status":       "not started",
        "keywords":                 extract(
            strip_html(desc_html) + " " + strip_html(req_html),
            _KEYWORDS
        ),
        "notes":                    "",
    }


MANUAL_FIELDS = ["type", "fit", "application_status", "notes"]


def fetch_and_merge(token: str, output_path: Path | None = None) -> dict:
    """Fetch all saved jobs and merge with existing CSV. Returns a status dict."""
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "jobs.csv"

    items = fetch_all(token)
    new_rows = {str(r["job_id"]): r for r in (parse_item(i) for i in items)}

    preserved, added = 0, 0
    if output_path.exists():
        with open(output_path, newline="", encoding="utf-8") as f:
            existing = {row["job_id"]: row for row in csv.DictReader(f)}
        for job_id, row in new_rows.items():
            if job_id in existing:
                for field in MANUAL_FIELDS:
                    row[field] = existing[job_id].get(field, "")
                preserved += 1
            else:
                added += 1
    else:
        added = len(new_rows)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(new_rows.values())

    return {"total": len(new_rows), "preserved": preserved, "added": added}


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
    result = fetch_and_merge(token, Path(args.output))
    print(f"Done. {result['total']} jobs saved "
          f"({result['preserved']} updated, {result['added']} new).")


if __name__ == "__main__":
    main()
