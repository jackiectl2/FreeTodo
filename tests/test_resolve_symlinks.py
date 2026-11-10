import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "free-todo-frontend" / "scripts" / "resolve-symlinks.js"


def test_resolver_materializes_root_package_without_expanding_pnpm(tmp_path: Path):
    node_modules = tmp_path / "node_modules"
    package = node_modules / ".pnpm" / "demo@1.0.0" / "node_modules" / "demo"
    dependency = node_modules / ".pnpm" / "dep@1.0.0" / "node_modules" / "dep"
    package.mkdir(parents=True)
    dependency.mkdir(parents=True)
    (package / "index.js").write_text("module.exports = 'demo';\n")
    (dependency / "index.js").write_text("module.exports = 'dep';\n")

    internal_link = package.parent / "dep"
    internal_link.symlink_to(dependency, target_is_directory=True)
    root_link = node_modules / "demo"
    root_link.symlink_to(package, target_is_directory=True)

    env = os.environ.copy()
    env["FREETODO_STANDALONE_NODE_MODULES"] = str(node_modules)
    subprocess.run(["node", str(SCRIPT)], env=env, check=True, capture_output=True, text=True)

    assert root_link.is_dir()
    assert not root_link.is_symlink()
    assert (root_link / "index.js").read_text() == "module.exports = 'demo';\n"
    assert internal_link.is_symlink(), "pnpm's internal link must remain untouched"
    assert dependency.is_dir()


def test_resolver_refuses_links_outside_standalone(tmp_path: Path):
    node_modules = tmp_path / "standalone" / "node_modules"
    external = tmp_path / "external-package"
    node_modules.mkdir(parents=True)
    external.mkdir()
    (external / "index.js").write_text("module.exports = 'external';\n")
    package_link = node_modules / "external"
    package_link.symlink_to(external, target_is_directory=True)

    env = os.environ.copy()
    env["FREETODO_STANDALONE_NODE_MODULES"] = str(node_modules)
    result = subprocess.run(
        ["node", str(SCRIPT)], env=env, check=True, capture_output=True, text=True
    )

    assert package_link.is_symlink()
    assert "refusing to follow a link outside standalone" in result.stderr
