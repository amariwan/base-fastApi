from __future__ import annotations

from collections.abc import Mapping

from utils.datetime_utils import get_current_iso_timestamp
from utils.journey_utils import Step, log_journey


class JourneyTracker:
    """Tracks the steps of a journey for logging purposes."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.steps: list[Step] = []
        self.success = True

    def add_step(self, description: str, data: Mapping[str, object] | None = None) -> None:
        """Add a step to the journey with description and optional data."""
        self.steps.append(
            {
                "step": description,
                "data": dict(data) if data is not None else {},
                "timestamp": get_current_iso_timestamp(),
            }
        )

    def set_failure(self) -> None:
        """Mark the journey as failed."""
        self.success = False

    def log_journey(self) -> None:
        """Log the completed journey."""
        log_journey(self.request_id, self.success, self.steps)
