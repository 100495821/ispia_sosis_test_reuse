#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

FRONTEND_PM=""
if command -v npm >/dev/null 2>&1; then
  FRONTEND_PM="npm"
elif command -v pnpm >/dev/null 2>&1; then
  FRONTEND_PM="pnpm"
elif command -v yarn >/dev/null 2>&1; then
  FRONTEND_PM="yarn"
else
  echo "[error] No JavaScript package manager found (npm/pnpm/yarn)."
  echo "[hint] Install Node.js (includes npm), then re-run this script."
  echo "[hint] macOS Homebrew: brew install node"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup] Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

echo "[setup] Installing Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt" > /dev/null

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "[setup] Installing frontend dependencies with ${FRONTEND_PM}..."
  if [[ "$FRONTEND_PM" == "npm" ]]; then
    (cd "$FRONTEND_DIR" && npm install > /dev/null)
  elif [[ "$FRONTEND_PM" == "pnpm" ]]; then
    (cd "$FRONTEND_DIR" && pnpm install > /dev/null)
  else
    (cd "$FRONTEND_DIR" && yarn install > /dev/null)
  fi
fi

echo "[start] Starting backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd "$BACKEND_DIR"
  exec "$VENV_DIR/bin/python" -m uvicorn api:app --host 127.0.0.1 --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "[start] Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "$FRONTEND_DIR"
  if [[ "$FRONTEND_PM" == "npm" ]]; then
    exec npm run dev -- --port "$FRONTEND_PORT"
  elif [[ "$FRONTEND_PM" == "pnpm" ]]; then
    exec pnpm run dev -- --port "$FRONTEND_PORT"
  else
    exec yarn dev --port "$FRONTEND_PORT"
  fi
) &
FRONTEND_PID=$!

cleanup() {
  echo
  echo "[stop] Shutting down services..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 3

if command -v open >/dev/null 2>&1; then
  open "http://localhost:${FRONTEND_PORT}"
fi

echo "[ready] Frontend: http://localhost:${FRONTEND_PORT}"
echo "[ready] Backend:  http://127.0.0.1:${BACKEND_PORT}"
echo "[info] Press Ctrl+C to stop both services."

wait "$BACKEND_PID" "$FRONTEND_PID"
