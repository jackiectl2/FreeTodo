from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / "scripts" / "macos" / "freetodo-common.sh"
DEV_LAUNCHER = REPO_ROOT / "Start-FreeTodo-Dev.command"
BUILD_INSTALLER = REPO_ROOT / "Build-and-Install-FreeTodo.command"


def run_zsh(
    command: str,
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        ["zsh", "-c", command],
        cwd=REPO_ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=check,
    )


def test_common_script_declares_canonical_data_path() -> None:
    result = run_zsh(f'source "{COMMON_SCRIPT}"; freetodo_app_data_dir')

    assert result.stdout.strip().endswith(
        "Library/Application Support/FreeTodo/lifetrace-data"
    )


def test_migration_copies_legacy_data_when_destination_is_empty(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    destination = tmp_path / "app-data"
    (source / "data").mkdir(parents=True)
    (source / "config").mkdir(parents=True)
    (source / "data" / "lifetrace.db").write_text("legacy database")
    (source / "config" / "config.yaml").write_text("api_key: local-only")

    run_zsh(
        f'source "{COMMON_SCRIPT}"; freetodo_migrate_legacy_data',
        env={
            "FREETODO_REPO_ROOT": str(REPO_ROOT),
            "FREETODO_LEGACY_DATA_DIR": str(source),
            "FREETODO_APP_DATA_DIR": str(destination),
        },
    )

    assert (destination / "data" / "lifetrace.db").read_text() == "legacy database"
    assert (destination / "config" / "config.yaml").read_text() == "api_key: local-only"


def test_migration_does_not_overwrite_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    destination = tmp_path / "app-data"
    (source / "data").mkdir(parents=True)
    (destination / "data").mkdir(parents=True)
    (source / "data" / "lifetrace.db").write_text("legacy database")
    (destination / "data" / "lifetrace.db").write_text("current database")

    result = run_zsh(
        f'source "{COMMON_SCRIPT}"; freetodo_migrate_legacy_data',
        env={
            "FREETODO_REPO_ROOT": str(REPO_ROOT),
            "FREETODO_LEGACY_DATA_DIR": str(source),
            "FREETODO_APP_DATA_DIR": str(destination),
        },
    )

    assert (destination / "data" / "lifetrace.db").read_text() == "current database"
    assert "already contains data" in result.stdout


def test_free_space_check_can_be_exercised_without_large_allocations(tmp_path: Path) -> None:
    success = run_zsh(
        f'source "{COMMON_SCRIPT}"; freetodo_require_free_space_gib 0 "{tmp_path}"'
    )
    failure = run_zsh(
        f'source "{COMMON_SCRIPT}"; freetodo_require_free_space_gib 999999 "{tmp_path}"',
        check=False,
    )

    assert success.returncode == 0
    assert failure.returncode != 0
    assert "Not enough free disk space" in failure.stderr


def test_dev_launcher_uses_canonical_data_and_source_servers() -> None:
    text = DEV_LAUNCHER.read_text()

    assert "freetodo_migrate_legacy_data" in text
    assert "LIFETRACE_DATA_DIR" in text
    assert "-m lifetrace.server" in text
    assert "pnpm dev" in text
    assert "freetodo_stop_stable_app" in text


def test_dev_launcher_has_process_cleanup_and_health_checks() -> None:
    text = DEV_LAUNCHER.read_text()

    assert "trap cleanup" in text
    assert "freetodo_wait_for_url" in text
    assert "http://127.0.0.1:8001/health" in text
    assert "http://127.0.0.1:3001" in text


def test_package_has_arm64_only_build_script() -> None:
    package = json.loads(
        (REPO_ROOT / "free-todo-frontend" / "package.json").read_text()
    )

    command = package["scripts"][
        "build:electron:web:pyinstaller:full:mac:arm64"
    ]
    assert "--mac --arm64" in command
    assert "--dir" in command


def test_backend_build_removes_only_pyinstaller_temporary_trees() -> None:
    text = (REPO_ROOT / "lifetrace" / "scripts" / "build-backend.sh").read_text()

    assert 'rm -rf "$LIFETRACE_DIR/build" "$LIFETRACE_DIR/dist"' in text
    assert 'rm -rf "$DIST_DIR"' not in text.split("Backend build complete!")[1]


def test_build_installer_preserves_app_data() -> None:
    text = BUILD_INSTALLER.read_text()

    assert "freetodo_migrate_legacy_data" in text
    assert "/Applications/FreeTodo.app" in text
    assert "freetodo_require_free_space_gib" in text
    assert "pnpm check" in text
    assert "pnpm type-check" in text
    for line in text.splitlines():
        if "rm " in line:
            assert "lifetrace-data" not in line


def test_build_installer_has_rollback_and_exact_artifact_checks() -> None:
    text = BUILD_INSTALLER.read_text()

    assert "backup_app" in text
    assert "rollback" in text
    assert "FreeTodo.app" in text
    assert "file \"$artifact/Contents/MacOS/FreeTodo\"" in text

