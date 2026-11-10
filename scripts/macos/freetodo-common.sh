#!/bin/zsh

# Shared macOS helpers for the stable app installer and source-backed dev launcher.
# This file is sourced by other scripts, so it deliberately does not enable shell options.

freetodo_app_data_dir() {
  print -r -- "${FREETODO_APP_DATA_DIR:-$HOME/Library/Application Support/FreeTodo/lifetrace-data}"
}

freetodo_migrate_legacy_data() {
  local repo_root="${FREETODO_REPO_ROOT:-${0:A:h:h:h}}"
  local source="${FREETODO_LEGACY_DATA_DIR:-$repo_root/local-user-data}"
  local destination="$(freetodo_app_data_dir)"

  if [[ ! -d "$source" ]]; then
    print -r -- "No legacy FreeTodo data found at: $source"
    return 0
  fi

  if [[ -d "$destination" ]] && \
    [[ -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    print -r -- "App data directory already contains data; migration skipped: $destination"
    return 0
  fi

  mkdir -p "${destination:h}"
  ditto "$source" "$destination"
  chmod 700 "$destination" 2>/dev/null || true
  print -r -- "Migrated FreeTodo data to: $destination"
}

freetodo_require_free_space_gib() {
  local required_gib="$1"
  local target="${2:-/}"
  local available_kib
  local required_kib

  if [[ "$required_gib" != <-> ]]; then
    print -u2 -r -- "Free-space requirement must be a non-negative integer GiB value."
    return 2
  fi

  available_kib="$(df -Pk "$target" | awk 'NR == 2 { print $4 }')"
  required_kib=$((required_gib * 1024 * 1024))
  if (( available_kib < required_kib )); then
    local available_gib=$((available_kib / 1024 / 1024))
    print -u2 -r -- \
      "Not enough free disk space: ${available_gib} GiB available, ${required_gib} GiB required."
    return 1
  fi
}

freetodo_stop_stable_app() {
  if [[ ! -d /Applications/FreeTodo.app ]]; then
    return 0
  fi

  osascript -e 'tell application id "com.freeugroup.freetodo" to quit' \
    >/dev/null 2>&1 || true

  local attempts=20
  while (( attempts > 0 )); do
    if ! pgrep -f '/Applications/FreeTodo.app/Contents/MacOS/FreeTodo' >/dev/null 2>&1; then
      break
    fi
    sleep 0.25
    attempts=$((attempts - 1))
  done

  pkill -TERM -f '/Applications/FreeTodo.app/Contents/MacOS/FreeTodo' \
    >/dev/null 2>&1 || true
  # A startup failure can leave the bundled backend orphaned after Electron
  # exits. Stop that exact executable as well so the next launch gets a clean
  # port and cannot accidentally reuse stale state.
  pkill -TERM -f '^/Applications/FreeTodo\.app/Contents/Resources/backend/lifetrace( |$)' \
    >/dev/null 2>&1 || true
}

freetodo_port_is_available() {
  local port="$1"
  ! /usr/sbin/lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

freetodo_wait_for_url() {
  local url="$1"
  local attempts="${2:-120}"
  local process_id="${3:-}"

  while (( attempts > 0 )); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -n "$process_id" ]] && ! kill -0 "$process_id" 2>/dev/null; then
      return 1
    fi
    sleep 1
    attempts=$((attempts - 1))
  done
  return 1
}

