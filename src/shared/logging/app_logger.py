"""Compatibility shim: provide module path `shared.logging.app_logger`.

Some code imports `shared.logging.app_logger` while the canonical module is
`shared.logging.AppLogger`. This small shim re-exports the expected symbols.
"""

from __future__ import annotations

from .AppLogger import (
    OperationLogger,
    fastapi_logger,
    journey_logger,
    setup_logging,
    single_logger,
    system_logger,
)

__all__ = [
    "fastapi_logger",
    "system_logger",
    "single_logger",
    "journey_logger",
    "OperationLogger",
    "setup_logging",
]
