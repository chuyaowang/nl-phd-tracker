# PhD Job Tracker

Fetch, browse, and track PhD job applications saved on [AcademicTransfer](https://www.academictransfer.com).

## Features

- Pulls all saved jobs from the AcademicTransfer API into a local CSV
- Extracts domain keywords (genomics, ML, neuroscience, organism model, etc.) to pre-populate notes
- Streamlit app for browsing and filtering jobs by status, type, and research fit
- Safe re-runs: manual edits to status, type, fit, and notes are preserved across refreshes

## Setup

**1. Clone and create the environment**
```bash
git clone https://github.com/chuyaowang/jobscraper.git
cd jobscraper
conda create -n jobscraper python=3.11 -y
conda activate jobscraper
pip install -r requirements.txt
```

**2. Add your API token**

Create a `.env` file in the project root:
```
AT_TOKEN=Bearer <your_token>
```

To get your token:
1. Log in to AcademicTransfer and go to your saved jobs page
2. Open DevTools (F12) → Network → Fetch/XHR → refresh the page
3. Find the request to `api.academictransfer.com/careers/vacancies/…is_favorite=true…`
4. Copy the `Authorization` header value

Tokens expire periodically — repeat this step when you get a 401 error.

## Usage

**Fetch saved jobs**
```bash
conda activate jobscraper
python src/fetch_saved_jobs.py
```

**Run the tracking app**
```bash
conda activate jobscraper
streamlit run src/app.py
```
Then open http://localhost:8501.

**Refresh keyword notes** (after editing `data/keywords.json`)
```bash
python src/update_notes.py
```

## Project structure

```
├── src/
│   ├── fetch_saved_jobs.py   # pulls jobs from the AcademicTransfer API
│   ├── extract_keywords.py   # domain keyword matching
│   ├── update_notes.py       # re-populate notes with keywords
│   └── app.py                # Streamlit tracking app
├── data/
│   └── keywords.json         # domain keyword definitions (edit to extend)
├── models/                   # future: trained type/fit classifiers
├── .env                      # your API token (never committed)
└── requirements.txt
```

## Tracking fields

In the app, select any job row to edit:

| Field | Options |
|---|---|
| **Status** | not started · applied · interviewing · rejected · offer |
| **Type** | computational · clinical · biological · bioinformatics |
| **Fit** | high · medium · low |
| **Notes** | free text (pre-populated with extracted keywords) |

## License

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for personal and academic use, not for commercial use.
