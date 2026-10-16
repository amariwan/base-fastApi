"""Conversation history values."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ConversationRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: ConversationRole
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("conversation message content must not be empty")
