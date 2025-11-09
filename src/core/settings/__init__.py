"""Settings management with singleton pattern."""

from __future__ import annotations

from collections.abc import Callable
from logging import getLogger
from typing import Generic, TypeVar

_logger = getLogger(__name__)

T = TypeVar('T')


class SettingsRegistry(Generic[T]):
    """Thread-safe singleton registry for settings instances.

    This class implements the Singleton pattern for settings objects,
    ensuring only one instance of each settings type exists throughout
    the application lifecycle.
    """

    def __init__(self):
        self._instances: dict[str, object] = {}

    def get_or_create(
        self,
        key: str,
        factory: Callable[[], T],
        *,
        suppress_errors: bool = False,
        default_factory: Callable[[], T] | None = None
    ) -> T:
        """Get existing instance or create new one.

        Args:
            key: Unique key for this settings type
            factory: Callable that creates the settings instance
            suppress_errors: If True, return default on error instead of raising
            default_factory: Fallback factory if main factory fails

        Returns:
            Settings instance

        Raises:
            Exception: If factory fails and suppress_errors is False
        """
        if key in self._instances:
            return self._instances[key]  # type: ignore

        try:
            instance = factory()  # type: ignore
            self._instances[key] = instance
            return instance  # type: ignore
        except Exception:
            if not suppress_errors:
                raise

            _logger.warning("Failed to create %s settings, using defaults!", key, exc_info=True)

            if default_factory is not None:
                instance = default_factory()  # type: ignore
            else:
                instance = factory()  # type: ignore

            self._instances[key] = instance
            return instance  # type: ignore

    def clear(self, key: str | None = None) -> None:
        """Clear cached instance(s).

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key is None:
            self._instances.clear()
        elif key in self._instances:
            del self._instances[key]


# Global registry instance
_registry = SettingsRegistry()


def get_settings_registry() -> SettingsRegistry:
    """Get the global settings registry."""
    return _registry
