import logging
from collections.abc import MutableMapping

from shared.logging.request_context import get_request_id


class LogTypeAdapter(logging.LoggerAdapter):
    """LoggerAdapter that enforces `log_type` and propagates request ids."""

    def process(
        self, msg: str, kwargs: MutableMapping[str, object] | None
    ) -> tuple[str, MutableMapping[str, object]]:
        payload: MutableMapping[str, object] = kwargs or {}
        extra = payload.get("extra")
        extra_map: MutableMapping[str, object] = extra if isinstance(extra, dict) else {}
        extra_map["log_type"] = getattr(self, "extra", {}).get("log_type", "SINGLE")

        request_id = get_request_id()
        if request_id:
            extra_map.setdefault("request_id", request_id)

        payload["extra"] = extra_map
        return msg, payload
