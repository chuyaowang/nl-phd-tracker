# PhD Job Tracker

Fetch, browse, and track PhD job applications saved on [AcademicTransfer](https://www.academictransfer.com).

## Features

- One-click sync via a Chrome extension — no manual token handling needed
- Pulls all saved jobs from the AcademicTransfer API into a local CSV
- Extracts domain keywords (genomics, ML, neuroscience, imaging, etc.) to pre-populate keyword tags
- Streamlit app for browsing and filtering jobs by status, type, and research fit
- Safe re-runs: manual edits to status, type, fit, and notes are preserved across syncs

## Setup

**1. Clone and create the environment**

```bash
git clone https://github.com/chuyaowang/jobscraper.git
cd jobscraper
conda create -n jobscraper python=3.11 -y
conda activate jobscraper
pip install -r requirements.txt
```

**2. Install the Chrome extension**

1. Open `chrome://extensions` in Chrome
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select the `extension/` folder
4. The extension icon appears in the toolbar — it shows a green **✓** badge once a token is captured

**3. Start the local sync server**

```bash
./start_server.sh
```

This starts a local FastAPI server at `http://127.0.0.1:8765` that the extension calls to trigger a sync.
Keep it running whenever you want to sync.

## Usage

### Primary workflow — browser extension

1. Log in to AcademicTransfer in Chrome (the extension auto-captures the token)
2. Click the extension icon → **Sync now**
3. In the Streamlit app, click **↻ Reload** in the sidebar to pick up the new data

### Run the tracking app

```bash
conda activate jobscraper
streamlit run src/app.py
```

Then open <http://localhost:8501>.

### Fallback — CLI sync

If you prefer not to use the extension, you can sync from the command line using a token from `.env`:

1. Log in to AcademicTransfer → DevTools (F12) → Network → Fetch/XHR → refresh the page
2. Find the request to `api.academictransfer.com/…is_favorite=true…` → copy the `Authorization` header
3. Create `.env` in the project root: `AT_TOKEN=Bearer <your_token>`
4. Run: `python src/fetch_saved_jobs.py`

Tokens expire periodically — repeat when you get a 401 error.

## Project structure

```
├── src/
│   ├── fetch_saved_jobs.py   # pulls jobs from the AcademicTransfer API
│   ├── extract_keywords.py   # domain keyword matching
│   ├── local_server.py       # FastAPI server for browser extension sync
│   └── app.py                # Streamlit tracking app
├── extension/                # Chrome extension (load unpacked from chrome://extensions)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
├── data/
│   └── keywords.json         # domain keyword definitions (edit to extend)
├── models/                   # future: trained type/fit classifiers
├── start_server.sh           # starts the local sync server
├── .env                      # your API token for CLI use (never committed)
└── requirements.txt
```

## Tracking fields

In the app, select any job row to edit:

| Field | Options |
|---|---|
| **Status** | not started · applied · interviewing · rejected · offer |
| **Type** | Computational · Clinical · Biological · Bioinformatics · Engineering |
| **Fit** | High · Medium · Low |
| **Keywords** | auto-populated from job text (read-only) |
| **Notes** | free text |

## License

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for personal and academic use, not for commercial use.