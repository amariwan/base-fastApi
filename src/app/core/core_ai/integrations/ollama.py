"""Ollama provider adapter and model discovery."""

from collections.abc import Callable
from urllib.parse import urlparse, urlunparse

import httpx
from app.core.core_ai.contracts import (
    AIProviderError,
    Capability,
    CapabilitySupport,
    ModelDescriptor,
    ProviderDescriptor,
)
from app.core.core_ai.integrations.pydantic_ai import PydanticAIProvider
from pydantic_ai.models import Model


class OllamaAIProvider(PydanticAIProvider):
    def __init__(
        self,
        descriptor: ProviderDescriptor,
        factory: Callable[[str], Model],
        *,
        base_url: str,
        timeout_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(descriptor, factory)
        parsed = urlparse(base_url)
        self._tags_url = urlunparse(parsed._replace(path="/api/tags", params="", query="", fragment=""))
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        try:
            if self._http_client is not None:
                response = await self._http_client.get(self._tags_url, timeout=self._timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(self._tags_url)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise AIProviderError("Ollama model discovery failed") from exc
        raw_models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(raw_models, list):
            raise AIProviderError("Ollama model discovery returned an invalid response")
        return tuple(self._descriptor_from_payload(model) for model in raw_models if isinstance(model, dict))

    def _descriptor_from_payload(self, payload: dict[str, object]) -> ModelDescriptor:
        model_id = payload.get("model") or payload.get("name")
        if not isinstance(model_id, str) or not model_id:
            raise AIProviderError("Ollama model discovery returned a model without an identifier")
        raw_capabilities = payload.get("capabilities")
        advertised = (
            {value for value in raw_capabilities if isinstance(value, str)}
            if isinstance(raw_capabilities, list)
            else set()
        )
        capability_map: dict[Capability, CapabilitySupport] = {}
        advertised_mapping = {
            "completion": Capability.TEXT_GENERATION,
            "tools": Capability.TOOL_CALLING,
            "embedding": Capability.EMBEDDINGS,
            "vision": Capability.VISION,
        }
        for advertised_name, capability in advertised_mapping.items():
            if advertised_name in advertised:
                capability_map[capability] = CapabilitySupport.VERIFIED
        details = payload.get("details")
        context_window = details.get("context_length") if isinstance(details, dict) else None
        return ModelDescriptor(
            provider_id=self.descriptor.provider_id,
            model_id=model_id,
            capabilities=capability_map,
            context_window=context_window if isinstance(context_window, int) else None,
        )
