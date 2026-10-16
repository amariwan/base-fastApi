"""Optional, tenant-isolated conversation storage."""

import asyncio
from typing import Protocol

from app.core.core_ai.memory.conversations import ConversationMessage


class ConversationStore(Protocol):
    async def append(self, tenant_id: str, conversation_id: str, message: ConversationMessage) -> None: ...

    async def list_messages(self, tenant_id: str, conversation_id: str) -> tuple[ConversationMessage, ...]: ...

    async def delete(self, tenant_id: str, conversation_id: str) -> int: ...


class InMemoryConversationStore:
    """Opt-in process-local history with a bounded retention window."""

    def __init__(self, *, max_messages_per_conversation: int = 100) -> None:
        if max_messages_per_conversation < 1:
            raise ValueError("max_messages_per_conversation must be positive")
        self._max_messages = max_messages_per_conversation
        self._messages: dict[tuple[str, str], list[ConversationMessage]] = {}
        self._lock = asyncio.Lock()

    async def append(self, tenant_id: str, conversation_id: str, message: ConversationMessage) -> None:
        self._validate_ids(tenant_id, conversation_id)
        key = (tenant_id, conversation_id)
        async with self._lock:
            messages = self._messages.setdefault(key, [])
            messages.append(message)
            del messages[: -self._max_messages]

    async def list_messages(self, tenant_id: str, conversation_id: str) -> tuple[ConversationMessage, ...]:
        self._validate_ids(tenant_id, conversation_id)
        async with self._lock:
            return tuple(self._messages.get((tenant_id, conversation_id), ()))

    async def delete(self, tenant_id: str, conversation_id: str) -> int:
        self._validate_ids(tenant_id, conversation_id)
        async with self._lock:
            messages = self._messages.pop((tenant_id, conversation_id), ())
        return len(messages)

    @staticmethod
    def _validate_ids(tenant_id: str, conversation_id: str) -> None:
        if not tenant_id or not conversation_id:
            raise ValueError("tenant_id and conversation_id are required")
