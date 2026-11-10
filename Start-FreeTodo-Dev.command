#!/bin/zsh
set -euo pipefail

REPO_ROOT="${0:A:h}"
FRONTEND_ROOT="$REPO_ROOT/free-todo-frontend"
COMMON_SCRIPT="$REPO_ROOT/scripts/macos/freetodo-common.sh"

source "$COMMON_SCRIPT"
export FREETODO_REPO_ROOT="$REPO_ROOT"

backend_pid=""
frontend_pid=""
cleanup_done=0

stop_tree() {
  local target_pid="$1"
  local child_pid
  for child_pid in $(pgrep -P "$target_pid" 2>/dev/null || true); do
    stop_tree "$child_pid"
  done
  kill -TERM "$target_pid" 2>/dev/null || true
}

cleanup() {
  if (( cleanup_done == 1 )); then
    return
  fi
  cleanup_done=1
  trap - INT TERM EXIT
  [[ -n "$frontend_pid" ]] && stop_tree "$frontend_pid"
  [[ -n "$backend_pid" ]] && stop_tree "$backend_pid"
  print -r -- "FreeTodo Dev stopped."
}
trap cleanup INT TERM EXIT

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 -r -- "FreeTodo Dev launcher currently supports macOS only."
  exit 1
fi

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  print -u2 -r -- "Python environment is missing: $REPO_ROOT/.venv"
  print -u2 -r -- "Run 'uv sync --group dev' in the repository first."
  exit 1
fi

if [[ ! -d "$FRONTEND_ROOT/node_modules" ]]; then
  print -u2 -r -- "Frontend dependencies are missing: $FRONTEND_ROOT/node_modules"
  print -u2 -r -- "Run 'pnpm install' in free-todo-frontend first."
  exit 1
fi

freetodo_stop_stable_app

if ! freetodo_port_is_available 8001; then
  print -u2 -r -- "Port 8001 is already in use. Stop the other dev backend first."
  exit 1
fi
if ! freetodo_port_is_available 3001; then
  print -u2 -r -- "Port 3001 is already in use. Stop the other dev frontend first."
  exit 1
fi

freetodo_migrate_legacy_data
export LIFETRACE_DATA_DIR="$(freetodo_app_data_dir)"
export FREETODO_GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
export NEXT_PUBLIC_API_URL="http://127.0.0.1:8001"
export PORT=3001

mkdir -p "$LIFETRACE_DATA_DIR/logs"
BACKEND_LOG="$LIFETRACE_DATA_DIR/logs/dev-backend-console.log"
FRONTEND_LOG="$LIFETRACE_DATA_DIR/logs/dev-frontend-console.log"

print -r -- "Starting FreeTodo Dev from: $REPO_ROOT"
print -r -- "Data directory: $LIFETRACE_DATA_DIR"

cd "$REPO_ROOT"
"$REPO_ROOT/.venv/bin/python" -m lifetrace.server >"$BACKEND_LOG" 2>&1 &
backend_pid=$!

if ! freetodo_wait_for_url "http://127.0.0.1:8001/health" 180 "$backend_pid"; then
  print -u2 -r -- "Backend failed to start. See: $BACKEND_LOG"
  exit 1
fi

cd "$FRONTEND_ROOT"
pnpm dev >"$FRONTEND_LOG" 2>&1 &
frontend_pid=$!

if ! freetodo_wait_for_url "http://127.0.0.1:3001" 180 "$frontend_pid"; then
  print -u2 -r -- "Frontend failed to start. See: $FRONTEND_LOG"
  exit 1
fi

open "http://127.0.0.1:3001"
print -r -- "FreeTodo Dev is ready at http://127.0.0.1:3001"
print -r -- "Frontend changes hot-reload. Restart this launcher after backend changes."
print -r -- "Keep this Terminal window open; press Control+C to stop."

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 2
done

print -u2 -r -- "A FreeTodo Dev service exited unexpectedly."
print -u2 -r -- "Backend log: $BACKEND_LOG"
print -u2 -r -- "Frontend log: $FRONTEND_LOG"
exit 1

