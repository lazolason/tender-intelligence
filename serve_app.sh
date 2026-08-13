#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-5001}"
export PORT
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

if [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
elif [ -f "venv/bin/activate" ]; then
  source "venv/bin/activate"
fi

GUNICORN_BIN=""
if [ -x ".venv/bin/gunicorn" ]; then
  GUNICORN_BIN=".venv/bin/gunicorn"
elif [ -x "venv/bin/gunicorn" ]; then
  GUNICORN_BIN="venv/bin/gunicorn"
elif command -v gunicorn >/dev/null 2>&1; then
  GUNICORN_BIN="$(command -v gunicorn)"
fi

if [ -n "$GUNICORN_BIN" ]; then
  exec "$GUNICORN_BIN" --config gunicorn.conf.py app:app
fi

echo "gunicorn not found; falling back to python3 app.py" >&2
exec python3 app.py
