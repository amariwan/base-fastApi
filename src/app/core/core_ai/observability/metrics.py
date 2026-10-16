"""Minimal observer-backed metrics without a mandatory exporter."""

from dataclasses import dataclass
from threading import Lock

from app.core.core_ai.observability.tracing import AIEvent


@dataclass(frozen=True, slots=True)
class AIMetricsSnapshot:
    operations: int
    failures: int
    duration_seconds: float
    input_tokens: int
    output_tokens: int
    model_requests: int
    tool_calls: int


class InMemoryAIMetrics:
    """Thread-safe observer for tests or exporter bridges."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._operations = 0
        self._failures = 0
        self._duration_seconds = 0.0
        self._input_tokens = 0
        self._output_tokens = 0
        self._model_requests = 0
        self._tool_calls = 0

    def record(self, event: AIEvent) -> None:
        with self._lock:
            self._operations += 1
            self._failures += int(not event.success)
            self._duration_seconds += event.duration_seconds
            if event.usage is not None:
                self._input_tokens += event.usage.input_tokens
                self._output_tokens += event.usage.output_tokens
                self._model_requests += event.usage.requests
                self._tool_calls += event.usage.tool_calls

    def snapshot(self) -> AIMetricsSnapshot:
        with self._lock:
            return AIMetricsSnapshot(
                operations=self._operations,
                failures=self._failures,
                duration_seconds=self._duration_seconds,
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                model_requests=self._model_requests,
                tool_calls=self._tool_calls,
            )
