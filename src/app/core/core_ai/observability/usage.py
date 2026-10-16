"""Provider-neutral usage normalization."""

from decimal import Decimal
from typing import Any

from app.core.core_ai.contracts import Usage


def usage_from_run(run_usage: Any) -> Usage:
    raw_cost = getattr(run_usage, "cost", None)
    estimated_cost = Decimal(str(raw_cost)) if raw_cost is not None else None
    return Usage(
        input_tokens=getattr(run_usage, "input_tokens", 0) or 0,
        output_tokens=getattr(run_usage, "output_tokens", 0) or 0,
        requests=getattr(run_usage, "requests", 0) or 0,
        tool_calls=getattr(run_usage, "tool_calls", 0) or 0,
        estimated_cost=estimated_cost,
    )
