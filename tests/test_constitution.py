"""Pruebas de la constitución: principios 1, 3 y 5 y RNF-3 (plan, sección 7.2)."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "habits"
TESTS_DIR = ROOT / "tests"

CORE_FORBIDDEN_IMPORTS = {"os", "sys", "json", "pathlib", "io"}
CORE_FORBIDDEN_CALLS = {"print", "open", "input"}
CORE_FORBIDDEN_ATTRIBUTES = {"today", "now"}
NETWORK_MODULES = {"socket", "urllib", "http", "ssl"}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _package_files() -> list[Path]:
    files = sorted(PACKAGE_DIR.glob("*.py"))
    assert {f.stem for f in files} >= {"core", "storage", "cli"}, "faltan módulos en habits/"
    return files


def _imported_modules(tree: ast.Module) -> set[str]:
    """Nombres de primer nivel importados; los imports relativos se ignoran."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_principle_1_only_standard_library_imports() -> None:
    allowed = set(sys.stdlib_module_names) | {"habits"}
    for path in _package_files():
        extra = _imported_modules(_parse(path)) - allowed
        assert not extra, f"{path.name} importa fuera de la biblioteca estándar: {sorted(extra)}"
    for path in sorted(TESTS_DIR.glob("*.py")):
        extra = _imported_modules(_parse(path)) - (allowed | {"pytest", "conftest"})
        assert not extra, f"{path.name} importa dependencias no permitidas: {sorted(extra)}"


def test_principle_3_core_is_pure() -> None:
    tree = _parse(PACKAGE_DIR / "core.py")
    forbidden = _imported_modules(tree) & CORE_FORBIDDEN_IMPORTS
    assert not forbidden, f"core.py importa módulos con I/O: {sorted(forbidden)}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in CORE_FORBIDDEN_CALLS, (
                f"core.py llama a {node.func.id}() en la línea {node.lineno}"
            )
        if isinstance(node, ast.Attribute):
            assert node.attr not in CORE_FORBIDDEN_ATTRIBUTES, (
                f"core.py lee el reloj con .{node.attr} en la línea {node.lineno}"
            )


def test_principle_3_cli_does_not_import_json() -> None:
    assert "json" not in _imported_modules(_parse(PACKAGE_DIR / "cli.py"))


def test_principle_5_json_only_imported_in_storage() -> None:
    for path in _package_files():
        if path.stem != "storage":
            assert "json" not in _imported_modules(_parse(path)), f"{path.name} importa json"


def test_rnf_3_no_network_modules_imported() -> None:
    for path in _package_files():
        found = _imported_modules(_parse(path)) & NETWORK_MODULES
        assert not found, f"{path.name} importa módulos de red: {sorted(found)}"
