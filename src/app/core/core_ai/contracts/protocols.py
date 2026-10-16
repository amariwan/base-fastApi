"""Outbound provider protocol implemented by integration adapters."""

from typing import Protocol, runtime_checkable

from app.core.core_ai.contracts.models import ModelDescriptor, ProviderDescriptor
from pydantic_ai.models import Model


@runtime_checkable
class AIProvider(Protocol):
    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def build_model(self, model_id: str) -> Model: ...

    async def discover_models(self) -> tuple[ModelDescriptor, ...]: ...
