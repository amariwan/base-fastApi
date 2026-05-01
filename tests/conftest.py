"""Global pytest configuration.

Provides:
- environment defaults for test runs
- automatic marker assignment (unit/integration/e2e) by path
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Keep DB off by default so local unit tests don't require DB drivers/services.
os.environ["DB_ENABLED"] = "false"
os.environ["MESSAGE_LANG"] = "de"
os.environ["API_PREFIX"] = "/api"

# Prefer local filesystem storage in tests to avoid requiring S3 credentials.
os.environ["STORAGE_BACKEND"] = "filesystem"
os.environ["FILESYSTEM_ROOT"] = tempfile.mkdtemp(prefix="tests-filesystem-")


def _has_marker(item: pytest.Item, name: str) -> bool:
    return any(mark.name == name for mark in item.iter_markers())


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign default markers from test path when not explicitly set."""
    for item in items:
        path = Path(str(item.fspath)).as_posix()
        filename = Path(path).name

        # Explicit route markers for centralized non-unit suites.
        if "/tests/e2e/" in path:
            if not _has_marker(item, "e2e"):
                item.add_marker(pytest.mark.e2e)
            continue

        if "/tests/integration/" in path:
            if not _has_marker(item, "integration"):
                item.add_marker(pytest.mark.integration)
            continue

        # Co-located test modules in app/** are unit tests by default.
        if "/app/" in path and (filename.endswith("_test.py") or filename.startswith("test_")):
            if not _has_marker(item, "unit"):
                item.add_marker(pytest.mark.unit)
            continue

        # Fallback: all remaining tests default to unit unless explicitly marked.
        if not any(_has_marker(item, marker) for marker in ("unit", "integration", "e2e")):
            if not _has_marker(item, "unit"):
                item.add_marker(pytest.mark.unit)
