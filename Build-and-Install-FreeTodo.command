#!/bin/zsh
set -euo pipefail

REPO_ROOT="${0:A:h}"
FRONTEND_ROOT="$REPO_ROOT/free-todo-frontend"
COMMON_SCRIPT="$REPO_ROOT/scripts/macos/freetodo-common.sh"
TARGET_APP="/Applications/FreeTodo.app"
ARTIFACT_ROOT="$FRONTEND_ROOT/dist-artifacts/electron/web/pyinstaller"

source "$COMMON_SCRIPT"
export FREETODO_REPO_ROOT="$REPO_ROOT"

staging_app="/Applications/.FreeTodo.app.installing.$$"
backup_app="/Applications/.FreeTodo.app.backup.$$"
install_complete=0

rollback() {
  local exit_code=$?
  trap - EXIT

  if [[ -d "$staging_app" ]]; then
    rm -rf -- "$staging_app"
  fi

  if (( install_complete == 0 )) && [[ -d "$backup_app" ]]; then
    if [[ -d "$TARGET_APP" ]]; then
      rm -rf -- "$TARGET_APP"
    fi
    mv "$backup_app" "$TARGET_APP"
    print -u2 -r -- "Installation failed; restored the previous FreeTodo.app."
  fi

  exit "$exit_code"
}
trap rollback EXIT

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  print -u2 -r -- "This local installer targets Apple Silicon macOS (arm64) only."
  exit 1
fi

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  print -u2 -r -- "Python environment is missing: $REPO_ROOT/.venv"
  exit 1
fi
if [[ ! -d "$FRONTEND_ROOT/node_modules" ]]; then
  print -u2 -r -- "Frontend dependencies are missing: $FRONTEND_ROOT/node_modules"
  exit 1
fi

freetodo_require_free_space_gib 3 "$REPO_ROOT"
freetodo_migrate_legacy_data

print -r -- "Running backend tests..."
cd "$REPO_ROOT"
"$REPO_ROOT/.venv/bin/pytest" -q

print -r -- "Running frontend checks..."
cd "$FRONTEND_ROOT"
pnpm check
pnpm type-check

print -r -- "Building Apple Silicon FreeTodo.app..."
pnpm build:electron:web:pyinstaller:full:mac:arm64

artifact="$(find "$ARTIFACT_ROOT" -type d -path '*/FreeTodo.app' -prune -print -quit)"
if [[ -z "$artifact" || ! -x "$artifact/Contents/MacOS/FreeTodo" ]]; then
  print -u2 -r -- "Build completed without a usable FreeTodo.app artifact."
  exit 1
fi

architecture="$(file "$artifact/Contents/MacOS/FreeTodo")"
if [[ "$architecture" != *"arm64"* ]]; then
  print -u2 -r -- "Unexpected app architecture: $architecture"
  exit 1
fi

print -r -- "Installing: $artifact"
freetodo_stop_stable_app

rm -rf -- "$staging_app"
ditto "$artifact" "$staging_app"

if [[ -d "$TARGET_APP" ]]; then
  rm -rf -- "$backup_app"
  mv "$TARGET_APP" "$backup_app"
fi

mv "$staging_app" "$TARGET_APP"
xattr -dr com.apple.quarantine "$TARGET_APP" 2>/dev/null || true

if [[ "${FREETODO_NO_OPEN:-0}" != "1" ]]; then
  open "$TARGET_APP"

  attempts=60
  while (( attempts > 0 )); do
    if pgrep -f '/Applications/FreeTodo.app/Contents/MacOS/FreeTodo' >/dev/null 2>&1; then
      break
    fi
    sleep 1
    attempts=$((attempts - 1))
  done

  if (( attempts == 0 )); then
    print -u2 -r -- "The installed app did not start; rolling back."
    exit 1
  fi
fi

install_complete=1
if [[ -d "$backup_app" ]]; then
  rm -rf -- "$backup_app"
fi
trap - EXIT

print -r -- "FreeTodo.app installed successfully: $TARGET_APP"
print -r -- "User data preserved at: $(freetodo_app_data_dir)"

