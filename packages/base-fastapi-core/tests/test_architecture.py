"""Guard against importing the hosting application from the library."""

from __future__ import annotations

import ast
from pathlib import Path


def test_library_never_imports_host_app() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "base_fastapi_core"
    forbidden: list[str] = []
    for module_path in source_root.rglob("*.py"):
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(name.name == "app" or name.name.startswith("app.") for name in node.names):
                    forbidden.append(str(module_path))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "app" or (node.module or "").startswith("app."):
                    forbidden.append(str(module_path))
    assert not forbidden, f"Library imports host application: {sorted(set(forbidden))}"
