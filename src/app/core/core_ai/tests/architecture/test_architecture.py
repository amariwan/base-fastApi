# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

import ast
from pathlib import Path

CORE_AI_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = CORE_AI_ROOT.parents[1] / "services"


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(path for path in root.rglob("*.py") if "tests" not in path.parts and "__pycache__" not in path.parts)


def test_core_ai_does_not_import_business_services() -> None:
    violations: list[str] = []
    for path in _python_files(CORE_AI_ROOT):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            if (module and module.startswith("app.services")) or any(name.startswith("app.services") for name in names):
                violations.append(str(path.relative_to(CORE_AI_ROOT)))
    assert violations == []


def test_business_application_layers_do_not_import_concrete_ai_sdks() -> None:
    violations: list[str] = []
    for path in SERVICES_ROOT.rglob("application/**/*.py"):
        source = path.read_text()
        if "pydantic_ai" in source or "app.core.core_ai" in source:
            violations.append(str(path.relative_to(SERVICES_ROOT)))
    assert violations == []


def test_contracts_do_not_depend_on_core_ai_implementation_packages() -> None:
    violations: list[str] = []
    for path in _python_files(CORE_AI_ROOT / "contracts"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if node.module.startswith("app.core.core_ai") and not node.module.startswith("app.core.core_ai.contracts"):
                violations.append(str(path.relative_to(CORE_AI_ROOT)))
    assert violations == []
