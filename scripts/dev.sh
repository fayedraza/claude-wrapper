#!/usr/bin/env bash
# Start (or stop) the backend + frontend dev servers, with an upfront
# ANTHROPIC_API_KEY check -- the Settings Router calls Claude directly
# (`anthropic.Anthropic()`, env-based auth) and fails with an opaque
# "Could not resolve authentication method" error if the key never made it
# into the backend process's environment. Run from anywhere in the repo.
#
# Usage:
#   scripts/dev.sh          Start Redis (best-effort), backend, frontend
#   scripts/dev.sh --stop   Stop whatever this script started
#   scripts/dev.sh --status Show whether each service is currently up

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
RUN_DIR="$REPO_ROOT/.dev"
LOG_DIR="$RUN_DIR/logs"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_PORT=8000
FRONTEND_PORT=3000

mkdir -p "$LOG_DIR"

# ---- helpers ----------------------------------------------------------

pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid_file() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

port_listening() {
  local port="$1"
  lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local log_file="$3"
  local attempts=30
  for ((i = 1; i <= attempts; i++)); do
    if curl -sf -o /dev/null "$url"; then
      return 0
    fi
    sleep 1
  done
  echo "error: $label did not come up at $url after ${attempts}s -- last log lines:" >&2
  tail -n 40 "$log_file" >&2 || true
  return 1
}

# ---- API key check ------------------------------------------------------

check_api_key() {
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "ANTHROPIC_API_KEY is set in the current shell -- using it."
    return 0
  fi

  local env_file="$BACKEND_DIR/.env"
  if [[ -f "$env_file" ]] && grep -qE '^ANTHROPIC_API_KEY=.+' "$env_file"; then
    echo "ANTHROPIC_API_KEY found in backend/.env -- will load it via 'uv run --env-file'."
    return 0
  fi

  cat >&2 <<EOF
error: ANTHROPIC_API_KEY is not set.

The Settings Router (POST /api/settings/propose) calls Claude directly and
will fail with a 502 settings.llm_error ("Could not resolve authentication
method...") without it. Fix one of:

  1. Add it to backend/.env:
       cp backend/.env.example backend/.env   # if you haven't already
       echo 'ANTHROPIC_API_KEY=sk-ant-...' >> backend/.env

  2. Export it in your shell before running this script:
       export ANTHROPIC_API_KEY=sk-ant-...

  3. Or run 'ant auth login' instead (see README.md "Settings Router").
EOF
  return 1
}

# ---- start ---------------------------------------------------------------

start_redis() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found -- skipping Redis (not required by any current feature yet)."
    return 0
  fi
  echo "Starting Redis via docker compose..."
  if ! (cd "$REPO_ROOT" && docker compose up -d redis) >"$LOG_DIR/redis.log" 2>&1; then
    echo "warning: could not start Redis -- continuing without it (see $LOG_DIR/redis.log)." >&2
  fi
}

start_backend() {
  local existing_pid
  existing_pid="$(read_pid_file "$BACKEND_PID_FILE")"
  if pid_running "$existing_pid" || port_listening "$BACKEND_PORT"; then
    echo "Backend already running on :$BACKEND_PORT -- skipping."
    return 0
  fi

  echo "Starting backend (FastAPI) on :$BACKEND_PORT..."
  (
    cd "$BACKEND_DIR"
    exec uv run --env-file .env uvicorn gateway.main:app --reload --port "$BACKEND_PORT"
  ) >"$LOG_DIR/backend.log" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"

  wait_for_http "http://localhost:$BACKEND_PORT/health" "backend" "$LOG_DIR/backend.log"
  echo "Backend healthy: http://localhost:$BACKEND_PORT"
}

start_frontend() {
  local existing_pid
  existing_pid="$(read_pid_file "$FRONTEND_PID_FILE")"
  if pid_running "$existing_pid" || port_listening "$FRONTEND_PORT"; then
    echo "Frontend already running on :$FRONTEND_PORT -- skipping."
    return 0
  fi

  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Installing frontend dependencies (npm install)..."
    (cd "$FRONTEND_DIR" && npm install) >"$LOG_DIR/frontend-install.log" 2>&1
  fi

  echo "Starting frontend (Next.js) on :$FRONTEND_PORT..."
  (
    cd "$FRONTEND_DIR"
    exec npm run dev
  ) >"$LOG_DIR/frontend.log" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"

  wait_for_http "http://localhost:$FRONTEND_PORT" "frontend" "$LOG_DIR/frontend.log"
  echo "Frontend up: http://localhost:$FRONTEND_PORT"
}

do_start() {
  check_api_key
  start_redis
  start_backend
  start_frontend
  cat <<EOF

Everything is up:
  Frontend  http://localhost:$FRONTEND_PORT
  Backend   http://localhost:$BACKEND_PORT  (http://localhost:$BACKEND_PORT/health)
  Logs      $LOG_DIR/
  Stop      scripts/dev.sh --stop
EOF
}

# ---- stop ------------------------------------------------------------

stop_one() {
  local label="$1"
  local pid_file="$2"
  local port="$3"
  local pid
  pid="$(read_pid_file "$pid_file")"

  if pid_running "$pid"; then
    echo "Stopping $label (pid $pid)..."
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      pid_running "$pid" || break
      sleep 0.5
    done
    pid_running "$pid" && kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"

  # Fall back to whatever's actually bound to the port (e.g. started outside
  # this script, or a --reload subprocess this script's pid doesn't cover).
  if port_listening "$port"; then
    local port_pid
    port_pid="$(lsof -i ":$port" -sTCP:LISTEN -t | head -n1)"
    echo "Port $port still in use by pid $port_pid -- stopping it too."
    kill "$port_pid" 2>/dev/null || true
  fi
}

do_stop() {
  stop_one "backend" "$BACKEND_PID_FILE" "$BACKEND_PORT"
  stop_one "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_PORT"
  echo "Stopped. (Redis, if running, is left up -- 'docker compose down' to stop it.)"
}

# ---- status ------------------------------------------------------------

do_status() {
  if port_listening "$BACKEND_PORT"; then
    echo "backend:  up   http://localhost:$BACKEND_PORT"
  else
    echo "backend:  down"
  fi
  if port_listening "$FRONTEND_PORT"; then
    echo "frontend: up   http://localhost:$FRONTEND_PORT"
  else
    echo "frontend: down"
  fi
}

# ---- entrypoint --------------------------------------------------------

case "${1:-}" in
  --stop) do_stop ;;
  --status) do_status ;;
  "") do_start ;;
  *)
    echo "usage: $0 [--stop|--status]" >&2
    exit 1
    ;;
esac
