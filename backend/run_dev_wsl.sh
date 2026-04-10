#!/usr/bin/env bash
# Run from inside backend/. Uses .venv-wsl on Linux (not Windows .venv).
# Default POC port 8787 (avoids conflicts with other apps on 8000). Override: PORT=9000 ./run_dev_wsl.sh
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8787}"
if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${PORT}"; then
  echo "Port ${PORT} is already in use. Listeners:"
  ss -tlnp 2>/dev/null | grep ":${PORT}" || ss -tln | grep ":${PORT}"
  echo ""
  echo "Free it (WSL):  fuser -k ${PORT}/tcp    # add sudo if needed"
  echo "Or use another port:  PORT=8001 $0"
  echo "Also check: another terminal, Windows uvicorn on same port, or Docker."
  exit 1
fi

VENV="$(pwd)/.venv-wsl"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

if [ ! -x "$PY" ]; then
  echo "Creating WSL venv at .venv-wsl..."
  python3 -m venv "$VENV"
  "$PIP" install -U pip wheel -q
fi
# Always sync: requirements change (e.g. google-generativeai → google-genai) and Kali blocks system pip (PEP 668).
echo "Syncing requirements.txt into .venv-wsl (use .venv-wsl/bin/pip — not system pip)..."
"$PIP" install -r requirements.txt -q

rm -rf app/__pycache__
# 0.0.0.0: listen on all interfaces so Windows can proxy to WSL IP (not just Linux localhost)
echo "Listening on 0.0.0.0:${PORT} (set PORT=... to change)"
exec "$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
