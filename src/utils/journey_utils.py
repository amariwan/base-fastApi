from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from shared.logging.AppLogger import journey_logger


class Step(TypedDict):
    step: str
    data: Mapping[str, object]
    timestamp: str


def log_journey(request_id: str, success: bool, steps: list[Step]) -> None:
    """Log the journey with the given request_id, success status, and steps."""
    journey_logger.info(
        "Journey log",
        extra={
            "log_type": "JOURNEY",
            "request_id": request_id,
            "success": success,
            "steps": steps,
        },
    )
