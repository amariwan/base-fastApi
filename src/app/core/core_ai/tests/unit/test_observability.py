# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

from decimal import Decimal

from app.core.core_ai.contracts import Usage
from app.core.core_ai.observability import AIEvent, InMemoryAIMetrics


def test_in_memory_metrics_aggregate_prompt_free_events() -> None:
    metrics = InMemoryAIMetrics()
    metrics.record(
        AIEvent(
            operation="generate",
            success=True,
            duration_seconds=0.25,
            provider_id="local",
            model_id="test",
            usage=Usage(
                input_tokens=3,
                output_tokens=5,
                requests=1,
                tool_calls=2,
                estimated_cost=Decimal("0.01"),
            ),
        )
    )
    metrics.record(AIEvent(operation="generate", success=False, duration_seconds=0.5, error_type="TimeoutError"))

    snapshot = metrics.snapshot()

    assert snapshot.operations == 2
    assert snapshot.failures == 1
    assert snapshot.duration_seconds == 0.75
    assert snapshot.input_tokens == 3
    assert snapshot.output_tokens == 5
    assert snapshot.model_requests == 1
    assert snapshot.tool_calls == 2
