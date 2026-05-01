from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping, Sequence
from contextvars import ContextVar, Token
from enum import StrEnum
from pathlib import Path
from typing import cast

_request_message_language: ContextVar[str | None] = ContextVar("request_message_language", default=None)


class ImproperlyConfiguredError(RuntimeError):
    """Raised when message files are missing or invalid."""


class MessageKeyLookup:
    def __init__(self, keys_enum: type[StrEnum]) -> None:
        self._keys_enum = keys_enum

    def __getattr__(self, name: str) -> str:
        try:
            return str(getattr(self._keys_enum, name))
        except AttributeError as exc:
            raise AttributeError(name) from exc


class MessageService:
    """Load and resolve localized messages from core and service-local JSON files."""

    def __init__(self, language: str | None = None, *, message_files: Sequence[Path] | None = None) -> None:
        self._logger = logging.getLogger("app_logger")
        raw_language = language if language is not None else (os.getenv("MESSAGE_LANG") or "de")
        self._language = raw_language.strip().lower() or "de"
        self._message_files = tuple(message_files) if message_files is not None else None
        self._messages_by_language: dict[str, dict[str, object]] = {}
        default_messages = self._load_for_language(self._language)
        self._keys_enum = self._build_keys_enum(default_messages)
        self._keys = MessageKeyLookup(self._keys_enum)

    @property
    def language(self) -> str:
        return self._language

    @property
    def keys(self) -> MessageKeyLookup:
        return self._keys

    @property
    def keys_enum(self) -> type[StrEnum]:
        return self._keys_enum

    def get(self, key: str | StrEnum, *, lang: str | None = None, **kwargs: object) -> str:
        lookup_key = str(key)
        messages = self._get_messages_for_language(lang)
        resolved = self._resolve(lookup_key, messages)
        if resolved is None:
            self._logger.warning("Missing message key: %s", lookup_key)
            return lookup_key

        if kwargs:
            try:
                return resolved.format(**kwargs)
            except Exception:
                self._logger.warning("Message interpolation failed for key: %s", lookup_key)
                return resolved
        return resolved

    def _resolve(self, dotted_key: str, messages: Mapping[str, object]) -> str | None:
        current: object = messages
        for part in dotted_key.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return None
            current = current[part]
        return current if isinstance(current, str) else None

    @property
    def default_language(self) -> str:
        return self._language

    @staticmethod
    def normalize_language(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        # Accept locale tags like de-DE / en_US and reduce to language part
        return normalized.replace("_", "-").split("-", 1)[0]

    def _effective_language(self, override: str | None) -> str:
        request_lang = self.normalize_language(_request_message_language.get())
        chosen = self.normalize_language(override) or request_lang or self._language
        return chosen or self._language

    def _get_messages_for_language(self, override: str | None) -> Mapping[str, object]:
        language = self._effective_language(override)
        try:
            return self._load_for_language(language)
        except ImproperlyConfiguredError:
            # Keep startup strict, but fallback at runtime if token locale is unsupported.
            if language != self._language:
                return self._load_for_language(self._language)
            raise

    def _load_for_language(self, language: str) -> dict[str, object]:
        cached = self._messages_by_language.get(language)
        if cached is not None:
            return cached
        files = self._message_files if self._message_files is not None else self._discover_message_files(language)
        loaded = self._load_messages(files)
        self._messages_by_language[language] = loaded
        return loaded

    def _discover_message_files(self, language: str) -> tuple[Path, ...]:
        app_root = Path(__file__).resolve().parents[2]
        core_file = Path(__file__).resolve().parent / f"messages.{language}.json"
        if not core_file.exists():
            raise ImproperlyConfiguredError(f"Message file not found: {core_file}")

        files: list[Path] = [core_file]
        services_root = app_root / "services"
        if not services_root.exists():
            return tuple(files)

        for service_dir in sorted(services_root.iterdir()):
            if not service_dir.is_dir() or service_dir.name.startswith("__"):
                continue
            message_dir = service_dir / "messages"
            if not message_dir.exists():
                continue
            message_file = message_dir / f"messages.{language}.json"
            if not message_file.exists():
                raise ImproperlyConfiguredError(f"Message file not found: {message_file}")
            files.append(message_file)

        return tuple(files)

    def _load_messages(self, message_files: Sequence[Path]) -> dict[str, object]:
        merged: dict[str, object] = {}
        for file_path in message_files:
            loaded = self._load_message_file(file_path)
            self._merge_dicts(merged, loaded, source=file_path)
        return merged

    def _load_message_file(self, file_path: Path) -> dict[str, object]:
        try:
            with file_path.open("r", encoding="utf-8") as file:
                loaded: object = json.load(file)
        except json.JSONDecodeError as exc:
            raise ImproperlyConfiguredError(f"Invalid JSON in message file {file_path}: {exc}") from exc
        except OSError as exc:
            raise ImproperlyConfiguredError(f"Unable to read message file {file_path}: {exc}") from exc

        if not isinstance(loaded, dict):
            raise ImproperlyConfiguredError(f"Message file {file_path} must contain a JSON object at the top level")
        return cast(dict[str, object], loaded)

    def _merge_dicts(
        self, target: dict[str, object], source_dict: Mapping[str, object], *, source: Path, prefix: str = ""
    ) -> None:
        for key, value in source_dict.items():
            dotted_key = f"{prefix}.{key}" if prefix else key
            existing = target.get(key)

            if isinstance(value, Mapping):
                if existing is None:
                    nested_target: dict[str, object] = {}
                    target[key] = nested_target
                elif isinstance(existing, dict):
                    nested_target = existing
                else:
                    raise ImproperlyConfiguredError(
                        f"Conflicting message key '{dotted_key}' in {source}: expected object, found string"
                    )
                self._merge_dicts(nested_target, cast(Mapping[str, object], value), source=source, prefix=dotted_key)
                continue

            if not isinstance(value, str):
                raise ImproperlyConfiguredError(f"Message key '{dotted_key}' in {source} must resolve to a string")
            if existing is None:
                target[key] = value
                continue
            raise ImproperlyConfiguredError(f"Duplicate message key '{dotted_key}' found in {source}")

    @staticmethod
    def _build_keys_enum(messages: Mapping[str, object]) -> type[StrEnum]:
        keys = MessageService._flatten_keys(messages)
        members = {MessageService._to_enum_name(key): key for key in sorted(keys)}
        if not members:
            members = {"ROOT": "root"}
        return cast(type[StrEnum], StrEnum("MessageKeys", members))

    @staticmethod
    def _flatten_keys(node: Mapping[str, object], prefix: str = "") -> list[str]:
        keys: list[str] = []
        for key, value in node.items():
            dotted = f"{prefix}.{key}" if prefix else key
            if isinstance(value, Mapping):
                keys.extend(MessageService._flatten_keys(cast(Mapping[str, object], value), dotted))
            elif isinstance(value, str):
                keys.append(dotted)
        return keys

    @staticmethod
    def _to_enum_name(key: str) -> str:
        sanitized = "".join(ch if ch.isalnum() else "_" for ch in key).upper().strip("_")
        if not sanitized:
            return "KEY"
        if sanitized[0].isdigit():
            return f"KEY_{sanitized}"
        return sanitized


def set_request_message_language(language: str | None) -> Token[str | None]:
    normalized = MessageService.normalize_language(language)
    return _request_message_language.set(normalized)


def reset_request_message_language(token: Token[str | None]) -> None:
    _request_message_language.reset(token)
