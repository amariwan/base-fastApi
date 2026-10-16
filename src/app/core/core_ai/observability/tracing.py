"""Prompt-free observability contracts and stdlib logging adapter."""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.core_ai.contracts import Usage


@dataclass(frozen=True, slots=True)
class AIEvent:
    operation: str
    success: bool
    duration_seconds: float
    provider_id: str | None = None
    model_id: str | None = None
    usage: Usage | None = None
    error_type: str | None = None


class AIObserver(Protocol):
    def record(self, event: AIEvent) -> None: ...


class LoggingAIObserver:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("app_logger")

    def record(self, event: AIEvent) -> None:
        usage = event.usage
        self._logger.info(
            "AI operation=%s success=%s provider=%s model=%s duration_seconds=%.6f "
            "input_tokens=%s output_tokens=%s requests=%s tool_calls=%s error_type=%s",
            event.operation,
            event.success,
            event.provider_id,
            event.model_id,
            event.duration_seconds,
            usage.input_tokens if usage else None,
            usage.output_tokens if usage else None,
            usage.requests if usage else None,
            usage.tool_calls if usage else None,
            event.error_type,
        )


class NullAIObserver:
    def record(self, event: AIEvent) -> None:
        del event
