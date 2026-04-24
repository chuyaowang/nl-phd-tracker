# CLAUDE.md — PhD Job Tracker

## Project purpose

Fetches the user's saved (favourited) PhD job listings from AcademicTransfer into
a CSV, and provides a Streamlit app for browsing and tracking application progress.
Future goal: train classifiers to auto-predict `type` and `fit` for new jobs based
on keywords and titles, removing the need for manual labelling.

## Environment

Conda environment name: **`jobscraper`** (Python 3.11).
Direct dependencies: `requests`, `beautifulsoup4`, `lxml`, `streamlit`, `fastapi`, `uvicorn`.
Full pinned versions in `requirements.txt`.

---

## Directory layout

```
academic/
├── src/                        # all Python source modules
│   ├── __init__.py
│   ├── fetch_saved_jobs.py     # data fetching entry point + fetch_and_merge()
│   ├── extract_keywords.py     # keyword matching module
│   ├── local_server.py         # FastAPI server for browser extension sync
│   └── app.py                  # Streamlit app
├── extension/                  # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js           # service worker: captures Bearer token
│   ├── content.js              # reads token from localStorage on page load
│   ├── popup.html              # extension popup UI
│   └── popup.js
├── data/
│   ├── keywords.json           # domain keyword definitions (tracked in git)
│   └── jobs.csv                # output data (gitignored — personal)
├── models/                     # future: trained type/fit classifiers
│   └── .gitkeep
├── .env                        # API token (gitignored — secret)
├── .gitignore
├── requirements.txt
├── start_server.sh             # starts local_server.py in the jobscraper env
├── instructions.md             # Instructions on how to use the software
├── CLAUDE.md                   # Instructions for Claude coding agent
└── README.md                   # Project README
```

All paths in `src/` scripts resolve relative to `Path(__file__).parent.parent`
(the project root), so scripts are always run from the project root:

```bash
python src/fetch_saved_jobs.py
streamlit run src/app.py
./start_server.sh
```

---

## Modularity rules

- **One responsibility per file.** Do not merge modules to save lines.
- `extract_keywords.py` — pure keyword logic; no CSV I/O, no API calls.
- `fetch_saved_jobs.py` — API fetching, merge logic, CSV writing. Imports from
  `extract_keywords`. No Streamlit. Exposes `fetch_and_merge(token)` for use by
  both the CLI entry point and `local_server.py`.
- `local_server.py` — FastAPI server only. Calls `fetch_and_merge`. No Streamlit,
  no direct CSV I/O.
- `app.py` — Streamlit UI only. Reads/writes CSV via `save_edit()`. No API calls.
- Future ML code (training, prediction) goes in its own `src/predict.py` module
  and is imported by both `fetch_saved_jobs.py` (auto-label new jobs) and `app.py`
  (show predictions alongside manual labels) — never inlined into either.
- `data/keywords.json` is the single source of truth for domain terms. Both
  `extract_keywords.py` and future ML feature engineering should read from it.

---

## src/fetch_saved_jobs.py

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

HTML fields are processed by `strip_html()` before writing to CSV:
- `<a href>` links are preserved as Markdown `[text](url)` (except `mailto:`)
- `get_text(separator="\n")` newlines around inline links are cleaned up by regex
- Contact name/email are parsed separately from the `mailto:` link in `additional_info`

### Flat description splitting

Some job posters put all content into `description` and leave the other HTML fields
empty. When `requirements` and `contract_terms` are both empty, `_split_description()`
scans the description HTML for `<strong>` section headers matching known patterns
(`"Job description"`, `"Job requirements"`, `"Conditions of employment"`) and splits
the content into the appropriate fields before stripping.

### Merge logic (safe re-runs)

`fetch_and_merge(token, output_path)` is the callable used by both CLI and server.
When `jobs.csv` already exists, it merges on `job_id`:

- **Existing jobs**: API fields are refreshed; `type`, `fit`, `application_status`,
  and `notes` are preserved. `keywords` is always refreshed from extracted text.
- **New jobs**: written with defaults (`application_status = "not started"`,
  `keywords` pre-populated with extracted keywords, `notes` empty).
- **Unsaved jobs**: removed (they no longer appear in the API response).

### CSV columns

```
url, job_id, title, institution, city, country,
deadline, date_posted, salary_min_eur, salary_max_eur,
weekly_hours, contract_duration,
job_description, requirements, conditions_of_employment,
employer, department, contact_name, contact_email,
type, fit, application_status, keywords, notes
```

---

## src/local_server.py

FastAPI server that the browser extension calls to trigger a sync.

```
POST /sync   { "token": "Bearer <jwt>" }  → runs fetch_and_merge, returns stats
GET  /status                              → last sync result or "No sync run yet"
```

Start with `./start_server.sh` (listens on `http://127.0.0.1:8765`).
The server must be running for the extension to work. CORS is open to all origins
(local-only server, no exposure risk).

---

## extension/

Chrome extension (Manifest V3). Load unpacked from `chrome://extensions`.

**Token capture** — two complementary mechanisms:
- `content.js` runs on every AcademicTransfer page at `document_idle`, scans
  `localStorage`/`sessionStorage` for a JWT token, and sends it to the background
  via `chrome.runtime.sendMessage`. Fires on page load, so the token is available
  immediately.
- `background.js` service worker also listens via `chrome.webRequest.onBeforeSendHeaders`
  on `api.academictransfer.com/*` to catch token refreshes from live API calls.

Both routes store the token in `chrome.storage.session` (cleared on browser close).
The extension badge shows a green **✓** when a token is stored.

**Sync flow**: click the popup → "Sync now" → popup reads the stored token and POSTs
to `http://localhost:8765/sync` → server runs `fetch_and_merge` → popup shows result.
Hit **↻ Reload** in the Streamlit app afterward to pick up the new data.

---

## src/extract_keywords.py

Loads `data/keywords.json` (category → list of terms) and searches job text for
matches using whole-word, case-insensitive regex. Returns matched terms as a
comma-separated string. Stateless — no side effects.

`data/keywords.json` categories: genomics & sequencing, proteomics & metabolomics,
cell biology, computational & ML, imaging & microscopy, neuroscience,
cancer & immunology, clinical & pathology, engineering & biophysics.

---

## src/app.py

### State management

Streamlit reruns the entire script on every interaction. To avoid data loss:

- **`st.session_state.df`** — loaded from CSV exactly once on first run. All edits
  update this in-memory copy. Filters and reruns never re-read the file.
- **`st.session_state.selected_idx`** — original DataFrame index of the selected
  row; persists across filter-triggered reruns that shift row positions.
- **`st.session_state.last_table_idx`** — the df-index last applied from a table
  click. `selected_idx` is only updated when this changes, preventing a stale table
  selection from overriding Prev/Next navigation on subsequent reruns (e.g. editing
  a field after navigating).
- **Widget keys include `idx`** (e.g. `sel_status_{idx}`) — forces Streamlit to
  reset edit widgets when the user switches to a different row, preventing stale
  values from a previously selected job.
- **↻ Reload button** — the only way to re-read `jobs.csv` into session state
  (intended for after a sync via the extension or CLI).

### Tracking fields and options

```python
STATUS_OPTIONS = ["not started", "applied", "interviewing", "rejected", "offer"]
TYPE_OPTIONS   = ["Computational", "Clinical", "Biological", "Bioinformatics", "Engineering"]
FIT_OPTIONS    = ["High", "Medium", "Low"]   # user's research-fit evaluation
```

### Layout

- **Sidebar**: status / type / fit multiselect filters; expired-deadline toggle;
  per-status summary counts; reload button.
- **Overview table**: `st.dataframe` with `on_select="rerun"`. Columns: status
  emoji, title, institution, city, deadline, type, fit emoji, application_status.
  Fit is shown as emoji only (🟢/🟡/🔴) — the text label is redundant in the table.
- **Detail panel** (appears on row selection):
  - Metrics: institution, location, deadline, salary.
  - Edit row: Status · Type · Fit dropdowns + Notes text area + Keywords (read-only text).
  - Navigation: ← Prev · Save · Next → buttons; Prev/Next auto-save before switching.
  - Content tabs: Job Description · Requirements · Conditions of Employment ·
    Employer · Department · Contact.
  - Long text rendered via `md()`: collapses excess blank lines, then converts
    isolated `\n` to `\n\n` for Markdown paragraph breaks. Markdown links from
    `strip_html` are rendered as clickable links.

### Save behaviour

`save_edit()` updates `st.session_state.df` in place and writes the full DataFrame
back to `data/jobs.csv` (deadline re-formatted to `YYYY-MM-DD`). Only the four
manual fields (`type`, `fit`, `application_status`, `notes`) are written by the app;
all API-sourced fields (including `keywords`) are read-only in the app.

---

## ML roadmap (future: src/predict.py)

Goal: auto-predict `type` and `fit` for newly fetched jobs so manual labelling
is not needed.

**Training data**: `data/jobs.csv` rows where `type` and `fit` are non-empty.
**Features**: keyword presence vector from `extract_keywords.py` + bag-of-words
or TF-IDF on `title` + `job_description`.
**Models**: start simple (logistic regression / random forest via scikit-learn);
save to `models/type_classifier.pkl` and `models/fit_classifier.pkl`.

Integration points:

- `fetch_saved_jobs.py`: call `predict.predict_type_fit(row)` for new jobs
  (those not in existing CSV) if a trained model exists.
- `app.py`: optionally show model prediction alongside manual label to help the
  user decide.

When implementing, add `scikit-learn` and `pandas` to `requirements.txt`.
Model files go in `models/` and are gitignored — commit only the training script.

---

## Git practices

### What is tracked

- `src/` — all source code
- `extension/` — browser extension source
- `data/keywords.json` — keyword definitions (update and commit when you add terms)
- `requirements.txt`, `CLAUDE.md`, `instructions.md`, `.gitignore`, `start_server.sh`
- `models/.gitkeep` — keeps the directory in git without tracking model binaries

### What is never committed

- `.env` — contains your personal API token
- `data/jobs.csv` — personal application data with private notes
- `models/*.pkl / *.joblib / *.pt` — binary model files (share training scripts instead)

### Commit conventions

- **Commit `keywords.json` separately** whenever you add or remove domain terms,
  so the change is easy to review and revert.

### Branch strategy

- `main` — stable, working code only.
- Feature branches for anything experimental: `git checkout -b ml/type-classifier`
- Merge back to main only when the feature is complete and tested.
- ML experiments in particular should always be on a branch — a broken classifier
  must not block the fetch/app workflow on main.
- Keep CLAUDE.md, README.md, and instructions.md updated when new features are committed to the main branch.
