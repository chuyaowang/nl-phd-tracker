# PhD Job Tracker — Instructions

## What this does

Fetches all jobs you have saved ("favourited") on AcademicTransfer and writes them
to `data/jobs.csv` with full details: title, institution, location, deadline, job
description, requirements, conditions of employment, department, and contact info.

A Streamlit app (`src/app.py`) lets you browse jobs, filter by status/type/fit, and
edit your tracking fields — all saved back to `jobs.csv`.

## Environment setup

The conda environment is named **`jobscraper`** (Python 3.11).

To recreate it on a new machine:

```bash
conda create -n jobscraper python=3.11 -y
conda activate jobscraper
pip install -r requirements.txt
```

---

## Syncing jobs — primary workflow (browser extension)

The browser extension automatically captures your AcademicTransfer session token
and triggers a sync with one click — no manual token copying needed.

### First-time setup

1. Open `chrome://extensions` in Chrome
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select the `extension/` folder in the project root
4. The extension icon appears in the toolbar

### Starting the local server

The extension talks to a local FastAPI server that runs `fetch_saved_jobs.py` on
your machine. Start it before syncing:

```bash
./start_server.sh
```

You should see:

```
  PhD Job Tracker — local sync server
  Listening on http://127.0.0.1:8765
```

Keep this terminal open while you use the extension. Press **Ctrl+C** to stop it.

### Syncing

1. Log in to AcademicTransfer in Chrome
2. The extension badge shows a green **✓** once the token is captured (happens automatically on page load)
3. Click the extension icon → **Sync now**
4. The popup shows how many jobs were fetched, updated, and added
5. Switch to the Streamlit app and click **↻ Reload** in the sidebar to pick up the new data

---

## Syncing jobs — fallback workflow (CLI)

If you prefer the command line, or the extension is not available, you can sync
manually using a token stored in `.env`.

### Getting a token

1. Log in to AcademicTransfer in your browser
2. Press **F12** → **Network** tab → filter by **Fetch/XHR** → refresh the page
3. Find the request to `api.academictransfer.com/careers/vacancies/…is_favorite=true…`
4. Click it → **Headers** → copy the `Authorization` value (starts with `Bearer `)
5. Create (or update) `.env` in the project root:

   ```
   AT_TOKEN=Bearer <your_token_here>
   ```

**Tokens expire.** When the script fails with a 401/403 error, repeat the steps above.

### Running the fetch script

```bash
conda activate jobscraper
python src/fetch_saved_jobs.py
```

- Re-running is safe: your manually edited fields (`type`, `fit`,
  `application_status`, `notes`) are **preserved** for existing jobs. `keywords`
  is always refreshed from the job text.
- Jobs you newly saved on AcademicTransfer are added with defaults.
- Jobs you unsaved on AcademicTransfer are removed.

---

## Running the app

```bash
conda activate jobscraper
streamlit run src/app.py
```

Then open the locally hosted web app in your browser (usually <http://localhost:8501>).

### Tracking fields (editable in the app)

| Field | Options |
|---|---|
| `application_status` | not started · applied · interviewing · rejected · offer |
| `type` | Computational · Clinical · Biological · Bioinformatics · Engineering |
| `fit` | High · Medium · Low |
| `keywords` | auto-populated from job text (read-only) |
| `notes` | free text |

Select a job row in the table → edit the fields in the panel below → click **Save**
(or use **← Prev** / **Next →** to auto-save and navigate to adjacent jobs).

### Filters (sidebar)

- Application status (multi-select)
- Job type (multi-select)
- Fit (multi-select)
- Hide expired deadlines (toggle)

### Reloading data

After a sync (via the extension or CLI), click **↻ Reload** in the sidebar to
pick up the new data. The app does not auto-reload — your in-progress edits are
safe until you explicitly reload.

---

## Files in this project

| File / Directory | Purpose |
|---|---|
| `src/fetch_saved_jobs.py` | Fetches saved jobs from the AcademicTransfer API |
| `src/local_server.py` | FastAPI server — bridge between extension and fetch script |
| `src/extract_keywords.py` | Domain keyword matching |
| `src/app.py` | Streamlit tracking app |
| `extension/` | Chrome extension — install via `chrome://extensions` → Load unpacked |
| `start_server.sh` | Starts the local sync server |
| `data/keywords.json` | Keyword definitions (edit to add domain terms) |
| `data/jobs.csv` | Your job tracker output (not committed — personal data) |
| `.env` | API token for CLI use (not committed — secret) |
| `requirements.txt` | Python dependencies |
| `CLAUDE.md` | Context for Claude Code when improving the scripts |