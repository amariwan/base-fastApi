"""External model-provider adapters."""

from app.core.core_ai.integrations.ollama import OllamaAIProvider
from app.core.core_ai.integrations.pydantic_ai import PydanticAIProvider

__all__ = ["OllamaAIProvider", "PydanticAIProvider"]
