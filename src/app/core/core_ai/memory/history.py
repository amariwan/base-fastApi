"""Pure conversation-history policies."""

from collections.abc import Sequence

from app.core.core_ai.memory.conversations import ConversationMessage


def trim_history(messages: Sequence[ConversationMessage], *, max_characters: int) -> tuple[ConversationMessage, ...]:
    if max_characters < 1:
        raise ValueError("max_characters must be positive")
    selected: list[ConversationMessage] = []
    used = 0
    for message in reversed(messages):
        if selected and used + len(message.content) > max_characters:
            break
        selected.append(message)
        used += len(message.content)
    return tuple(reversed(selected))
