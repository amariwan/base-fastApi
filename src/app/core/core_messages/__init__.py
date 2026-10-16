from __future__ import annotations

from .loader import (
    ImproperlyConfiguredError,
    MessageKeyLookup,
    MessageService,
    reset_request_message_language,
    set_request_message_language,
)

_msg = MessageService()
msg = _msg
MessageKeys = _msg.keys

__all__ = [
    "MessageKeyLookup",
    "set_request_message_language",
    "reset_request_message_language",
    "ImproperlyConfiguredError",
    "MessageKeys",
    "MessageService",
    "msg",
]
