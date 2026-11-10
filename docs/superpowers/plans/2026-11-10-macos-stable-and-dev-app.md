# macOS Stable and Dev App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a double-clickable Apple Silicon `FreeTodo.app`, a source-backed `FreeTodo Dev` launcher, and a safe one-click build/install workflow that preserves the user's existing local data.

**Architecture:** Keep source code in the Personal Projects Git worktree, but make `~/Library/Application Support/FreeTodo/lifetrace-data` the canonical runtime-data directory for both stable and dev modes. The stable Electron app embeds a snapshot of the Next.js frontend and PyInstaller backend; source changes enter the stable app only through an explicit arm64 rebuild and atomic reinstall. The dev launcher runs Python and Next.js directly from the repository and shares the canonical data directory, while preventing concurrent stable/dev execution.

**Tech Stack:** zsh, Electron, electron-builder, Next.js standalone, Python 3.12, PyInstaller, SQLite, macOS Application Support and `/Applications`

**Spec:** `LOCAL-PRODUCT-ROADMAP_CN.md`

## Global Constraints

- Target this MacBook Air's Apple Silicon `arm64` architecture only for the first local build.
- Never commit API keys or any file under `local-user-data/` or `~/Library/Application Support/FreeTodo/`.
- Do not delete or overwrite the legacy data directory during migration.
- Do not run stable and dev backends concurrently against the same SQLite database.
- Installed app updates must preserve `~/Library/Application Support/FreeTodo/lifetrace-data`.
- The build script must fail before a large build when free disk space is below its documented safety threshold.
- The first implementation is local and unsigned; GitHub release signing, notarization, and auto-update remain separate future work.

---

### Task 1: macOS Runtime and Migration Helpers

**Files:**
- Create: `scripts/macos/freetodo-common.sh`
- Create: `tests/test_macos_launchers.py`

**Interfaces:**
- Produces: `freetodo_app_data_dir`, `freetodo_migrate_legacy_data`, `freetodo_require_free_space_gib`, `freetodo_stop_stable_app`, and `freetodo_port_is_available` shell functions.
- Consumes: `FREETODO_APP_DATA_DIR` and `FREETODO_LEGACY_DATA_DIR` optional environment overrides for tests and worktrees.

- [ ] **Step 1: Write failing tests for canonical paths, non-destructive migration, and disk checks**

```python
def test_common_script_declares_canonical_data_path():
    result = run_zsh('source scripts/macos/freetodo-common.sh; freetodo_app_data_dir')
    assert result.stdout.strip().endswith("Library/Application Support/FreeTodo/lifetrace-data")

def test_migration_does_not_overwrite_existing_destination(tmp_path):
    source = tmp_path / "legacy"
    destination = tmp_path / "app-data"
    (source / "data").mkdir(parents=True)
    (destination / "data").mkdir(parents=True)
    (source / "data" / "lifetrace.db").write_text("legacy")
    (destination / "data" / "lifetrace.db").write_text("current")
    run_zsh(
        'source scripts/macos/freetodo-common.sh; freetodo_migrate_legacy_data',
        env={"FREETODO_LEGACY_DATA_DIR": str(source), "FREETODO_APP_DATA_DIR": str(destination)},
    )
    assert (destination / "data" / "lifetrace.db").read_text() == "current"
```

- [ ] **Step 2: Run the focused tests and verify they fail because the helper does not exist**

Run: `.venv/bin/pytest -q tests/test_macos_launchers.py`
Expected: FAIL with a missing `scripts/macos/freetodo-common.sh` error.

- [ ] **Step 3: Implement the shared helper with exact-target validation and `ditto` migration**

```zsh
freetodo_app_data_dir() {
  print -r -- "${FREETODO_APP_DATA_DIR:-$HOME/Library/Application Support/FreeTodo/lifetrace-data}"
}

freetodo_migrate_legacy_data() {
  local source="${FREETODO_LEGACY_DATA_DIR:-$FREETODO_REPO_ROOT/local-user-data}"
  local destination="$(freetodo_app_data_dir)"
  [[ -d "$source" ]] || return 0
  if [[ -e "$destination" && -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    return 0
  fi
  mkdir -p "${destination:h}"
  ditto "$source" "$destination"
}
```

- [ ] **Step 4: Run the focused tests and shell syntax check**

Run: `.venv/bin/pytest -q tests/test_macos_launchers.py && zsh -n scripts/macos/freetodo-common.sh`
Expected: PASS.

- [ ] **Step 5: Commit the helper and tests**

```bash
git add scripts/macos/freetodo-common.sh tests/test_macos_launchers.py
git commit -m "feat(mac): add runtime data helpers"
```

### Task 2: Source-Backed FreeTodo Dev Launcher

**Files:**
- Create: `Start-FreeTodo-Dev.command`
- Modify: `tests/test_macos_launchers.py`

**Interfaces:**
- Consumes: shared helpers from `scripts/macos/freetodo-common.sh` and the repository `.venv` and `free-todo-frontend/node_modules`.
- Produces: a double-clickable launcher that starts backend port 8001 and frontend port 3001 from source, using the canonical app-data directory.

- [ ] **Step 1: Add failing launcher contract tests**

```python
def test_dev_launcher_uses_canonical_data_and_source_servers():
    text = Path("Start-FreeTodo-Dev.command").read_text()
    assert "freetodo_migrate_legacy_data" in text
    assert "LIFETRACE_DATA_DIR" in text
    assert "python -m lifetrace.server" in text
    assert "pnpm dev" in text
```

- [ ] **Step 2: Run the focused test and verify the launcher is missing**

Run: `.venv/bin/pytest -q tests/test_macos_launchers.py`
Expected: FAIL because `Start-FreeTodo-Dev.command` does not exist.

- [ ] **Step 3: Implement the launcher with traps, health checks, and stable-app shutdown**

```zsh
#!/bin/zsh
set -euo pipefail
REPO_ROOT="${0:A:h}"
source "$REPO_ROOT/scripts/macos/freetodo-common.sh"
export FREETODO_REPO_ROOT="$REPO_ROOT"
freetodo_stop_stable_app
freetodo_migrate_legacy_data
export LIFETRACE_DATA_DIR="$(freetodo_app_data_dir)"
export FREETODO_GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
"$REPO_ROOT/.venv/bin/python" -m lifetrace.server &
backend_pid=$!
cd "$REPO_ROOT/free-todo-frontend"
pnpm dev &
frontend_pid=$!
trap 'kill -TERM $frontend_pid $backend_pid 2>/dev/null || true' INT TERM EXIT
open http://127.0.0.1:3001
wait "$frontend_pid"
```

- [ ] **Step 4: Mark the launcher executable and run syntax/contract tests**

Run: `chmod +x Start-FreeTodo-Dev.command && zsh -n Start-FreeTodo-Dev.command && .venv/bin/pytest -q tests/test_macos_launchers.py`
Expected: PASS.

- [ ] **Step 5: Commit the dev launcher**

```bash
git add Start-FreeTodo-Dev.command tests/test_macos_launchers.py
git commit -m "feat(mac): add source dev launcher"
```

### Task 3: Apple Silicon Build and Install Script

**Files:**
- Create: `Build-and-Install-FreeTodo.command`
- Modify: `free-todo-frontend/package.json`
- Modify: `tests/test_macos_launchers.py`

**Interfaces:**
- Consumes: shared helpers, Electron's `web.pyinstaller` configuration, repository tests, and the existing `.venv`/`node_modules`.
- Produces: `build:electron:web:pyinstaller:full:mac:arm64` and a double-clickable build/install workflow that installs only the exact `FreeTodo.app` target.

- [ ] **Step 1: Add failing tests for arm64-only build and safe install semantics**

```python
def test_package_has_arm64_only_build_script():
    package = json.loads(Path("free-todo-frontend/package.json").read_text())
    command = package["scripts"]["build:electron:web:pyinstaller:full:mac:arm64"]
    assert "--mac --arm64" in command

def test_build_installer_preserves_app_data():
    text = Path("Build-and-Install-FreeTodo.command").read_text()
    assert "freetodo_migrate_legacy_data" in text
    assert "/Applications/FreeTodo.app" in text
    assert "lifetrace-data" not in " ".join(line for line in text.splitlines() if "rm " in line)
```

- [ ] **Step 2: Run focused tests and verify the build script contracts are missing**

Run: `.venv/bin/pytest -q tests/test_macos_launchers.py`
Expected: FAIL for the missing package script and command file.

- [ ] **Step 3: Add the arm64 package script**

```json
"build:electron:web:pyinstaller:full:mac:arm64": "pnpm build:frontend:web && pnpm build:backend:pyinstaller && pnpm electron:resolve-symlinks && pnpm electron:copy-missing-deps && pnpm build:electron:web:pyinstaller:frontend-shell && electron-builder --config electron-builder.web.pyinstaller.yml --mac --arm64"
```

- [ ] **Step 4: Implement build, exact-artifact discovery, backup, install, smoke check, and rollback**

```zsh
freetodo_require_free_space_gib 3
freetodo_migrate_legacy_data
pnpm check
pnpm type-check
"$REPO_ROOT/.venv/bin/pytest" -q
pnpm build:electron:web:pyinstaller:full:mac:arm64
artifact="$(find "$FRONTEND_ROOT/dist-artifacts/electron/web/pyinstaller" -type d -path '*/FreeTodo.app' -print -quit)"
[[ -n "$artifact" ]] || exit 1
ditto "$artifact" "$staging_app"
mv "$staging_app" /Applications/FreeTodo.app
open -a /Applications/FreeTodo.app
```

- [ ] **Step 5: Run syntax, contract, frontend, and backend tests**

Run: `zsh -n Build-and-Install-FreeTodo.command && .venv/bin/pytest -q tests/test_macos_launchers.py && cd free-todo-frontend && pnpm check && pnpm type-check`
Expected: PASS.

- [ ] **Step 6: Commit the build/install workflow**

```bash
git add Build-and-Install-FreeTodo.command free-todo-frontend/package.json tests/test_macos_launchers.py
git commit -m "feat(mac): add one-click app installer"
```

### Task 4: User Documentation and Migration Runbook

**Files:**
- Modify: `LOCAL-MIGRATION-GUIDE.md`
- Modify: `LOCAL-PRODUCT-ROADMAP_CN.md`
- Create: `MAC-APP-GUIDE_CN.md`

**Interfaces:**
- Consumes: the launcher names, canonical data directory, and stable/dev separation implemented above.
- Produces: an exact Chinese runbook for daily use, source development, rebuilds, data backups, recovery, and Mac mini migration.

- [ ] **Step 1: Document daily stable use and dev-mode rules**

```markdown
## 两种运行模式

- 稳定版：双击 `/Applications/FreeTodo.app`。
- 开发版：双击仓库根目录的 `Start-FreeTodo-Dev.command`。
- 两种模式共享 `~/Library/Application Support/FreeTodo/lifetrace-data`，不可同时运行。
```

- [ ] **Step 2: Document the one-time migration and update procedure**

```markdown
第一次构建会在目标数据目录为空时复制旧的 `local-user-data/`。以后更新只替换应用代码，不覆盖数据目录。修改源码后双击 `Build-and-Install-FreeTodo.command`，测试与构建成功后才替换稳定版 App。
```

- [ ] **Step 3: Update the roadmap checkboxes only for delivered packaging work**

Run: `rg -n '桌面端|Build|Application Support|Habitica|手机端' LOCAL-PRODUCT-ROADMAP_CN.md MAC-APP-GUIDE_CN.md LOCAL-MIGRATION-GUIDE.md`
Expected: desktop packaging delivered; mobile and Habitica remain deferred.

- [ ] **Step 4: Commit the documentation**

```bash
git add LOCAL-MIGRATION-GUIDE.md LOCAL-PRODUCT-ROADMAP_CN.md MAC-APP-GUIDE_CN.md
git commit -m "docs(mac): explain stable and dev workflows"
```

### Task 5: Build, Install, and End-to-End Smoke Test

**Files:**
- Verify only; generated artifacts and user data remain untracked.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: `/Applications/FreeTodo.app`, migrated canonical data, and an evidence-backed build report.

- [ ] **Step 1: Record pre-build data hashes and free space**

Run: `shasum -a 256 local-user-data/data/lifetrace.db && df -h /`
Expected: hash and available space recorded without modifying data.

- [ ] **Step 2: Run the one-click installer with the legacy data override from the main worktree**

Run: `FREETODO_LEGACY_DATA_DIR=/Users/ctl/Local_Documents/1_personal_projs/FreeTodo/local-user-data ./Build-and-Install-FreeTodo.command`
Expected: tests pass, arm64 App builds, data migrates once, App installs and opens.

- [ ] **Step 3: Verify architecture, code signature status, processes, and health endpoints**

Run: `file /Applications/FreeTodo.app/Contents/MacOS/FreeTodo; codesign -dv --verbose=2 /Applications/FreeTodo.app; pgrep -fl FreeTodo`
Expected: arm64 executable, local/ad-hoc or unsigned status documented, and running app processes.

- [ ] **Step 4: Verify migrated data without exposing secrets**

Run: `shasum -a 256 "$HOME/Library/Application Support/FreeTodo/lifetrace-data/data/lifetrace.db"`
Expected: database hash matches the pre-build legacy database hash.

- [ ] **Step 5: Open the app and verify the five existing todos appear**

Expected: stable App window loads and the existing todo data is visible; no API key is printed or committed.

- [ ] **Step 6: Run final regression and inspect repository status**

Run: `.venv/bin/pytest -q && cd free-todo-frontend && pnpm check && pnpm type-check && git status --short`
Expected: checks pass and only intentionally generated ignored artifacts exist.

- [ ] **Step 7: Commit any final test-only corrections**

```bash
git add Build-and-Install-FreeTodo.command Start-FreeTodo-Dev.command \
  scripts/macos/freetodo-common.sh tests/test_macos_launchers.py \
  free-todo-frontend/package.json MAC-APP-GUIDE_CN.md \
  LOCAL-MIGRATION-GUIDE.md LOCAL-PRODUCT-ROADMAP_CN.md
git commit -m "fix(mac): finalize local app installation"
```

