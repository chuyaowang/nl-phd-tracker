# PhD Job Tracker — Instructions

## What this does
Fetches all jobs you have saved ("favourited") on AcademicTransfer and writes them
to `jobs.csv` with full details: title, institution, location, deadline, job
description, requirements, conditions of employment, department, and contact info.

A Streamlit app (`app.py`) lets you browse jobs, filter by status/type/fit, and
edit your tracking fields — all saved back to `jobs.csv`.

## Environment setup
The conda environment is named **`jobscraper`** (Python 3.11).

To recreate it on a new machine:
```bash
conda create -n jobscraper python=3.11 -y
pip install -r requirements.txt
```

## API token
Your token is stored in `.env` as `AT_TOKEN`. **Tokens expire.** When the script
fails with a 401/403 error, get a new one:

1. Log in to AcademicTransfer in your browser.
2. Go to your saved jobs page.
3. Press **F12** → **Network** tab → filter by **Fetch/XHR** → refresh the page.
4. Find the request to `api.academictransfer.com/careers/vacancies/…is_favorite=true…`
5. Click it → **Headers** → copy the `Authorization` value (starts with `Bearer `).
6. Paste it into `.env`, replacing the old value:
   ```
   AT_TOKEN=Bearer <new_token_here>
   ```

## Fetching / refreshing saved jobs
```bash
conda activate jobscraper
python fetch_saved_jobs.py
```

- Re-running is safe: your manually edited fields (`type`, `fit`,
  `application_status`, `notes`) are **preserved** for existing jobs.
- Jobs you newly saved on AcademicTransfer are added with defaults.
- Jobs you unsaved on AcademicTransfer are removed.

## Running the app
```bash
conda activate jobscraper
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

### Tracking fields (editable in the app)
| Field | Options |
|---|---|
| `application_status` | not started · applied · interviewing · rejected · offer |
| `type` | computational · clinical · biological · bioinformatics |
| `fit` | high · medium · low |
| `notes` | free text |

Select a job row in the table → edit the fields in the panel below → click **Save**.

### Filters (sidebar)
- Application status (multi-select)
- Job type (multi-select)
- Fit (multi-select)
- Hide expired deadlines (toggle)

### Reloading data in the app
If you re-run `fetch_saved_jobs.py` while the app is open, click **↻ Reload from CSV**
in the sidebar to pick up the new data.

## Files in this directory
| File | Purpose |
|---|---|
| `fetch_saved_jobs.py` | Fetches saved jobs from the AcademicTransfer API |
| `app.py` | Streamlit tracking app |
| `.env` | API token (do not share or commit) |
| `jobs.csv` | Output — your job tracker |
| `requirements.txt` | Python dependencies |
| `instructions.md` | This file |
| `CLAUDE.md` | Context for Claude Code when improving the scripts |
