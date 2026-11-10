from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "free-todo-frontend"
NEXT_SERVER = FRONTEND_ROOT / "electron" / "next-server.ts"
PYINSTALLER_SPEC = REPO_ROOT / "lifetrace" / "pyinstaller.spec"
RUNTIME_PATHS = FRONTEND_ROOT / "electron" / "runtime-paths.ts"


def test_electron_configs_copy_standalone_node_modules_explicitly():
    configs = sorted(FRONTEND_ROOT.glob("electron-builder*.yml"))
    assert configs

    for config in configs:
        text = config.read_text()
        assert "from: '.next/standalone/node_modules'" in text, config.name
        assert "to: 'standalone/node_modules'" in text, config.name
        assert "!**/.pnpm/**" not in text, config.name


def test_packaged_server_can_resolve_electron_production_dependencies():
    text = NEXT_SERVER.read_text()
    assert 'process.resourcesPath,\n\t\t"app",\n\t\t"node_modules"' in text
    assert "serverEnv.NODE_PATH" in text
    assert ".join(path.delimiter)" in text


def test_pyinstaller_collects_dynamically_registered_lifetrace_modules():
    text = PYINSTALLER_SPEC.read_text()
    assert 'lifetrace_dir.rglob("*.py")' in text
    assert '".".join(["lifetrace", *module_parts])' in text
    assert "hiddenimports.extend(lifetrace_submodules)" in text


def test_packaged_macos_runtime_stays_outside_signed_app_bundle():
    text = RUNTIME_PATHS.read_text()
    assert 'app.isPackaged && process.platform === "darwin"' in text
    assert 'app.getPath("userData")' in text
