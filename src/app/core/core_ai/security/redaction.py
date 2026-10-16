"""Small defensive redaction helpers for operational error metadata."""

import re

_SECRET_ASSIGNMENT = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*([^\s,;]+)")
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")


def redact_sensitive_text(value: str) -> str:
    """Redact common credential forms without logging or retaining the input."""

    redacted = _BEARER_TOKEN.sub("Bearer [REDACTED]", value)
    return _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
