"""Factory for OpenAI-compatible chat-completions endpoints."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def build_openai_compatible_model(model_id: str, *, base_url: str, api_key: str) -> OpenAIChatModel:
    return OpenAIChatModel(model_id, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
