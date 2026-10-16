"""Provider-neutral inference stream events."""

from dataclasses import dataclass
from enum import StrEnum

from app.core.core_ai.contracts.models import Usage


class StreamEventKind(StrEnum):
    DELTA = "delta"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class StreamEvent:
    kind: StreamEventKind
    delta: str | None = None
    usage: Usage | None = None
