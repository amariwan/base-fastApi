"""Factories for explicitly configured cloud model providers."""

from collections.abc import Callable

from app.core.core_ai.contracts import AIConfigurationError
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider


def cloud_model_factory(provider_id: str, api_key: str) -> Callable[[str], Model]:
    if provider_id == "openai":
        return lambda model_id: OpenAIResponsesModel(model_id, provider=OpenAIProvider(api_key=api_key))
    if provider_id == "anthropic":
        return lambda model_id: AnthropicModel(model_id, provider=AnthropicProvider(api_key=api_key))
    if provider_id == "google":
        return lambda model_id: GoogleModel(model_id, provider=GoogleProvider(api_key=api_key))
    if provider_id == "openrouter":
        return lambda model_id: OpenAIChatModel(
            model_id,
            provider=OpenAIProvider(base_url="https://openrouter.ai/api/v1", api_key=api_key),
        )
    raise AIConfigurationError(f"Unsupported cloud provider '{provider_id}'")
