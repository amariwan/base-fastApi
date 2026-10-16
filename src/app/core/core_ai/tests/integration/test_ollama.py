# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

import os

import pytest
from app.core.core_ai.contracts import ProviderDescriptor, ProviderLocation
from app.core.core_ai.integrations import OllamaAIProvider
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

OLLAMA_MODEL = os.getenv("AI_TEST_OLLAMA_MODEL")
OLLAMA_BASE_URL = os.getenv("AI_TEST_OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")


@pytest.mark.integration
@pytest.mark.skipif(not OLLAMA_MODEL, reason="AI_TEST_OLLAMA_MODEL is not configured")
@pytest.mark.asyncio
async def test_live_ollama_model_discovery() -> None:
    provider = OllamaAIProvider(
        ProviderDescriptor("ollama", ProviderLocation.LOCAL, configured=True),
        lambda model_id: OllamaModel(model_id, provider=OllamaProvider(base_url=OLLAMA_BASE_URL)),
        base_url=OLLAMA_BASE_URL,
        timeout_seconds=10,
    )

    models = await provider.discover_models()

    assert OLLAMA_MODEL in {model.model_id for model in models}
