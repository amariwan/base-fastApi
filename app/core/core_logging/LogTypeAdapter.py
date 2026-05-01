from __future__ import annotations

import logging
from collections.abc import MutableMapping


class LogTypeAdapter(logging.LoggerAdapter[logging.Logger]):
    def process(
        self,
        msg: object,
        kwargs: MutableMapping[str, object],
    ) -> tuple[object, MutableMapping[str, object]]:
        raw_extra = kwargs.get("extra")
        extra: dict[str, object] = raw_extra if isinstance(raw_extra, dict) else {}
        log_type = (self.extra or {}).get("log_type", "SINGLE")
        extra["log_type"] = log_type
        kwargs["extra"] = extra
        return msg, kwargs
