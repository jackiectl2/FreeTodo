from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "free-todo-frontend"
NEXT_SERVER = FRONTEND_ROOT / "electron" / "next-server.ts"
PYINSTALLER_SPEC = REPO_ROOT / "lifetrace" / "pyinstaller.spec"
RUNTIME_PATHS = FRONTEND_ROOT / "electron" / "runtime-paths.ts"
APP_ICON = FRONTEND_ROOT / "public" / "free-todo-logos" / "freetodotest-icon.png"
NEXT_CONFIG = FRONTEND_ROOT / "next.config.ts"
CONFIG_QUERY = FRONTEND_ROOT / "lib" / "query" / "config.ts"


def test_electron_configs_copy_standalone_node_modules_explicitly():
    configs = sorted(FRONTEND_ROOT.glob("electron-builder*.yml"))
    assert configs

    for config in configs:
        text = config.read_text()
        assert "from: '.next/standalone/node_modules'" in text, config.name
        assert "to: 'standalone/node_modules'" in text, config.name
        assert "!**/.pnpm/**" not in text, config.name


def test_electron_configs_use_freetodotest_identity_and_icon():
    configs = sorted(FRONTEND_ROOT.glob("electron-builder*.yml"))
    assert APP_ICON.is_file()

    for config in configs:
        text = config.read_text()
        assert "productName: FreeTodoTest" in text, config.name
        assert "com.jackiectl2.freetodotest" in text, config.name
        assert "public/free-todo-logos/freetodotest-icon.png" in text, config.name


def test_macos_icon_uses_standard_transparent_safe_margin():
    with Image.open(APP_ICON) as image:
        rgba = image.convert("RGBA")
        assert rgba.size == (1024, 1024)
        alpha_bounds = rgba.getchannel("A").getbbox()

    assert alpha_bounds is not None
    left, top, right, bottom = alpha_bounds
    assert left >= 95
    assert top >= 95
    assert right <= 929
    assert bottom <= 929


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


def test_production_image_cache_cannot_mutate_signed_app_bundle():
    text = NEXT_CONFIG.read_text()
    assert 'unoptimized: process.env.NODE_ENV === "production"' in text


def test_llm_status_rechecks_transient_unconfigured_startup_state():
    text = CONFIG_QUERY.read_text()
    assert "refetchInterval" in text
    assert "status?.configured ? false : 2000" in text
