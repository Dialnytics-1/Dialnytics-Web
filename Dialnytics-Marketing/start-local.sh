#!/bin/sh
set -eu
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
[ -f .env ] || .venv/bin/python -m app.manage setup
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
