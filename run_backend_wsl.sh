#!/usr/bin/env bash
# Run from repo root. Uses backend/.venv-wsl (Linux venv; separate from Windows .venv).
# Default POC port 8787. Override: PORT=9000 ./run_backend_wsl.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

PORT="${PORT:-8787}"
if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${PORT}"; then
  echo "Port ${PORT} is already in use. Listeners:"
  ss -tlnp 2>/dev/null | grep ":${PORT}" || ss -tln | grep ":${PORT}"
  echo ""
  echo "Free it (WSL):  fuser -k ${PORT}/tcp    # sudo if needed"
  echo "Or:  PORT=8001 $0"
  exit 1
fi

VENV="$ROOT/backend/.venv-wsl"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

if [ ! -x "$PY" ]; then
  echo "Creating WSL venv at backend/.venv-wsl..."
  python3 -m venv "$VENV"
  "$PIP" install -U pip wheel -q
fi
echo "Syncing backend/requirements.txt → .venv-wsl..."
"$PIP" install -r "$ROOT/backend/requirements.txt" -q

rm -rf app/__pycache__
# 0.0.0.0: required so Windows (Vite proxy) can reach this API via the WSL LAN IP; 127.0.0.1 alone → ERR_CONNECTION_RESET
echo "Listening on 0.0.0.0:${PORT}"
exec "$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
