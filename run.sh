#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Virtual environment not found. Running setup first..."
  bash ./setup.sh
fi

if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "The existing .venv does not use Python 3.10 or newer."
  echo "Rename or remove .venv manually, then run ./setup.sh."
  exit 1
fi

if ! .venv/bin/python -c 'import uvicorn' >/dev/null 2>&1; then
  echo "Server dependencies are missing. Running setup first..."
  bash ./setup.sh
fi

if ! .venv/bin/python -c 'import fastapi, uvicorn, jinja2, multipart, cv2, numpy, insightface, onnxruntime, PIL, itsdangerous, openpyxl' >/dev/null 2>&1; then
  echo "One or more application packages are missing. Running setup first..."
  bash ./setup.sh
  if ! .venv/bin/python -c 'import fastapi, uvicorn, jinja2, multipart, cv2, numpy, insightface, onnxruntime, PIL, itsdangerous, openpyxl' >/dev/null 2>&1; then
    echo "Application dependencies are still unavailable. Review the setup output above."
    exit 1
  fi
fi

if ! .venv/bin/python -c 'from backend.face_engine import ensure_models; ensure_models()'; then
  echo "Face recognition models are unavailable. Check your internet connection and run setup.sh."
  exit 1
fi

echo "Starting Face Attendance Kiosk on port 8000..."
.venv/bin/python -c "from backend.config import print_access_urls; print_access_urls()"
exec .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
