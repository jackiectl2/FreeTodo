from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / "scripts" / "macos" / "freetodo-common.sh"


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

