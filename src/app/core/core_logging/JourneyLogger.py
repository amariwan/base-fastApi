from __future__ import annotations

import datetime as dt

from app.core.core_logging.AppLogger import journey_logger


class JourneyTracker:
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.steps: list[dict[str, object]] = []
        self.success = True

    def add_step(
        self,
        description: str | None = None,
        data: dict[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        # Backward compatibility: support legacy 'descrption' keyword
        if description is None and "descrption" in kwargs:
            legacy = kwargs.pop("descrption")
            description = str(legacy) if legacy is not None else None

        self.steps.append(
            {
                "step": description,
                "data": data or {},
                "timestamp": dt.datetime.now(dt.UTC).isoformat(),
            }
        )

    def set_failure(self) -> None:
        self.success = False

    def log_journey(self) -> None:
        journey_logger.info(
            "Journey log",
            extra={
                "log_type": "JOURNEY",
                "request_id": self.request_id,
                "success": self.success,
                "steps": self.steps,
            },
        )
