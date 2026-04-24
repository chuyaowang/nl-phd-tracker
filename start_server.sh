#!/usr/bin/env bash
# Start the local sync server for the browser extension.
# Stop with Ctrl+C. Keep this terminal open while using the extension.
set -e
cd "$(dirname "$0")"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate jobscraper

echo ""
echo "  PhD Job Tracker — local sync server"
echo "  Listening on http://127.0.0.1:8765"
echo "  Stop with Ctrl+C"
echo ""

uvicorn src.local_server:app --host 127.0.0.1 --port 8765 --log-level warning
