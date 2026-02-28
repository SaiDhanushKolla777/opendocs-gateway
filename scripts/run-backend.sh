#!/bin/bash
# Run the API backend (from repo root).
# Ensure .venv exists in api/ and deps installed: cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="${PWD}/api"
mkdir -p api/data api/data/uploads
if [ -f api/.venv/bin/activate ]; then
  source api/.venv/bin/activate
fi
cd api && uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}" --reload
