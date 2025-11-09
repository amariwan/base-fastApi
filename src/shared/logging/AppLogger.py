from __future__ import annotations

"""Structured logging bootstrap and helpers."""

import json
import logging
import logging.config
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType

from config import get_app_settings
from shared.logging.LogTypeAdapter import LogTypeAdapter

_CONFIG_PATH = Path(__file__).parent / "logger_config_files" / "stdout_config.json"
_LOGGERS = ("app_logger", "system", "single", "journey")

fastapi_logger = logging.getLogger("app_logger")
system_logger = LogTypeAdapter(logging.getLogger("system"), {"log_type": "SYSTEM"})
single_logger = LogTypeAdapter(logging.getLogger("single"), {"log_type": "SINGLE"})
journey_logger = LogTypeAdapter(logging.getLogger("journey"), {"log_type": "JOURNEY"})


def _resolve_level(raw_level: object) -> str:
    """Convert enum-like values to a string level name."""
    value = getattr(raw_level, "value", raw_level)
    return str(value).upper()


def _load_config(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def setup_logging(*, force: bool = False) -> None:
    """Configure Python logging exactly once (unless `force=True`)."""
    if getattr(setup_logging, "_configured", False) and not force:
        return

    level = _resolve_level(get_app_settings().LOG_LEVEL)
    config = _load_config(_CONFIG_PATH)

    root_logger = config.setdefault("loggers", {}).setdefault("root", {})
    root_logger["level"] = level
    for name in _LOGGERS:
        logger_cfg = config["loggers"].get(name)
        if logger_cfg is not None:
            logger_cfg["level"] = level

    logging.config.dictConfig(config)
    setup_logging._configured = True  # type: ignore[attr-defined]


@dataclass(slots=True)
class OperationLogger:
    """Context manager for consistent start/end/error log statements."""

    logger: logging.LoggerAdapter[logging.Logger]
    operation: str
    context: Mapping[str, object] = field(default_factory=dict)
    _start_ns: int = field(init=False, default=0)

    def __enter__(self) -> OperationLogger:
        self._start_ns = time.perf_counter_ns()
        self.logger.info("starting %s", self.operation, extra=dict(self.context))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        duration_ms = int((time.perf_counter_ns() - self._start_ns) / 1_000_000)
        payload = {**self.context, "duration_ms": duration_ms}
        if exc is None:
            self.logger.info("completed %s", self.operation, extra=payload)
            return False
        self.logger.error(
            "failed %s", self.operation, extra={**payload, "error": str(exc)}
        )
        return False


__all__ = [
    "fastapi_logger",
    "system_logger",
    "single_logger",
    "journey_logger",
    "OperationLogger",
    "setup_logging",
]
