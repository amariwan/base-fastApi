"""Optional, tenant-isolated conversation history."""

from app.core.core_ai.memory.conversations import ConversationMessage, ConversationRole
from app.core.core_ai.memory.history import trim_history
from app.core.core_ai.memory.store import ConversationStore, InMemoryConversationStore

__all__ = [
    "ConversationMessage",
    "ConversationRole",
    "ConversationStore",
    "InMemoryConversationStore",
    "trim_history",
]
