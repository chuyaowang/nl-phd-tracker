# CLAUDE.md — PhD Job Tracker

## Project purpose
Fetches the user's saved (favourited) PhD job listings from AcademicTransfer into
a CSV, and provides a Streamlit app for browsing and tracking application progress.

## Environment
Conda environment name: **`jobscraper`** (Python 3.11).
Direct dependencies: `requests`, `beautifulsoup4`, `lxml`, `streamlit`.
Full pinned versions in `requirements.txt`.

## Files
| File | Role |
|---|---|
| `fetch_saved_jobs.py` | Pulls data from the AcademicTransfer API → `jobs.csv` |
| `app.py` | Streamlit app for browsing and editing tracking fields |
| `.env` | Holds `AT_TOKEN=Bearer <token>` (expires periodically) |
| `jobs.csv` | The output — both API data and manually edited fields |

---

## fetch_saved_jobs.py

### Data source
The AcademicTransfer REST API — no HTML scraping of individual pages.

```
GET https://api.academictransfer.com/careers/vacancies/
    ?is_favorite=true&is_active=all&ordering=-start_date&limit=100
Authorization: Bearer <token>
```

Pagination is handled via the `next` field in the response.
Token is read from `.env` (key: `AT_TOKEN`); falls back to `--token` CLI arg.

### API response structure (one item)
```
{
  "external_id": int,           # job ID used in the URL
  "absolute_url": str,
  "city": str,
  "country_code": str,          # ISO 2-letter
  "start_date": str,            # ISO datetime — date posted
  "end_date": str,              # ISO datetime — application deadline
  "min_salary": int,
  "max_salary": int,
  "min_weekly_hours": float,
  "max_weekly_hours": float,
  "translations": [{
    "language_code": "en",
    "title": str,
    "description": str,               # HTML
    "requirements": str,              # HTML
    "contract_terms": str,            # HTML — conditions of employment
    "contract_duration": str,         # plain text e.g. "4 years"
    "organisation_name": str,
    "organisation_description": str,  # HTML
    "department_name": str,
    "department_description": str,    # HTML
    "additional_info": str,           # HTML — contains mailto: contact link
  }]
}
```

HTML fields are stripped to plain text via BeautifulSoup before writing to CSV.
Contact name/email are parsed from the `mailto:` link inside `additional_info`.

### Merge logic (safe re-runs)
When `jobs.csv` already exists, the script merges on `job_id`:
- **Existing jobs**: API fields are refreshed; `type`, `fit`, `application_status`,
  and `notes` are preserved from the existing CSV.
- **New jobs**: written with defaults (`application_status = "not started"`,
  others blank).
- **Unsaved jobs**: removed (they no longer appear in the API response).

### CSV columns
```
url, job_id, title, institution, city, country,
deadline, date_posted, salary_min_eur, salary_max_eur,
weekly_hours, contract_duration,
job_description, requirements, conditions_of_employment,
employer, department, contact_name, contact_email,
type, fit, application_status, notes
```

---

## app.py

### State management
Streamlit reruns the entire script on every interaction. To avoid data loss:

- **`st.session_state.df`** — loaded from CSV exactly once on first run. All edits
  update this in-memory copy. Filters and reruns never re-read the file.
- **`st.session_state.selected_idx`** — original DataFrame index of the selected
  row; persists across filter-triggered reruns that shift row positions.
- **Widget keys include `idx`** (e.g. `sel_status_{idx}`) — forces Streamlit to
  reset edit widgets when the user switches to a different row, preventing stale
  values from a previously selected job.
- **↻ Reload button** — the only way to re-read `jobs.csv` into session state
  (intended for after `fetch_saved_jobs.py` is re-run).

### Tracking fields and options
```python
STATUS_OPTIONS = ["not started", "applied", "interviewing", "rejected", "offer"]
TYPE_OPTIONS   = ["computational", "clinical", "biological", "bioinformatics"]
FIT_OPTIONS    = ["high", "medium", "low"]   # user's research-fit evaluation
```

### Layout
- **Sidebar**: status / type / fit multiselect filters; expired-deadline toggle;
  per-status summary counts; reload button.
- **Overview table**: `st.dataframe` with `on_select="rerun"`. Columns: status
  emoji, title, institution, city, deadline, type, fit emoji, application_status.
  Fit is shown as emoji only (🟢/🟡/🔴) — text is redundant.
- **Detail panel** (appears on row selection):
  - Metrics: institution, location, deadline, salary.
  - Edit row: Status · Type · Fit dropdowns + Notes text area + Save button.
  - Content tabs: Job Description · Requirements · Conditions of Employment ·
    Employer · Department · Contact.
  - Long text rendered with `st.markdown(text.replace("\n", "\n\n"))` — single
    `\n` is ignored by Markdown; double `\n\n` creates paragraph breaks.

### Save behaviour
`save_edit()` updates `st.session_state.df` in place and writes the full DataFrame
back to `jobs.csv` (deadline column re-formatted to `YYYY-MM-DD`). Only the four
manual fields are written by the app; all API-sourced fields are read-only.
