"""
Local FastAPI server that receives a Bearer token from the browser extension
and triggers a full fetch+merge of saved jobs.

Start with: ./start_server.sh
"""

import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from fetch_saved_jobs import fetch_and_merge

app = FastAPI(title="PhD Job Tracker local server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_last_sync: dict | None = None


class SyncRequest(BaseModel):
    token: str


@app.post("/sync")
def sync(req: SyncRequest):
    global _last_sync
    if not req.token:
        raise HTTPException(status_code=400, detail="token is required")
    try:
        result = fetch_and_merge(req.token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _last_sync = {**result, "timestamp": datetime.now().isoformat(timespec="seconds")}
    return _last_sync


@app.get("/status")
def status():
    return _last_sync or {"message": "No sync run yet"}