import asyncio

import httpx

# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101, S106
import pytest
from app.core.core_ai.agents import RegisteredTool, ToolRegistry
from app.core.core_ai.bootstrap import build_ai_client
from app.core.core_ai.config import AISettings
from app.core.core_ai.contracts import (
    AIConfigurationError,
    AIProviderError,
    AIRequest,
    AIRequestLimitError,
    AIRequestTimeoutError,
    AIResult,
    Capability,
    CapabilitySupport,
    ModelDescriptor,
    ModelNotFoundError,
    PrivacyRequirement,
    ProviderDescriptor,
    ProviderLocation,
    StreamEventKind,
    ToolPermissionDeniedError,
)
from app.core.core_ai.inference import (
    AIClientDependencies,
    AIClientLimits,
    AIInferenceClient,
    ModelRouter,
    RoutingPolicy,
)
from app.core.core_ai.integrations import OllamaAIProvider
from app.core.core_ai.observability import AIEvent
from app.core.core_ai.registry import ModelRegistry, ProviderRegistry
from app.core.core_ai.security import redact_sensitive_text
from pydantic import BaseModel, SecretStr, ValidationError
from pydantic_ai import Tool
from pydantic_ai.models.test import TestModel


class Answer(BaseModel):
    value: int


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[AIEvent] = []

    def record(self, event: AIEvent) -> None:
        self.events.append(event)


class FakeProvider:
    descriptor = ProviderDescriptor(
        provider_id="fake",
        location=ProviderLocation.LOCAL,
        configured=True,
        available=True,
    )

    def __init__(self, model: TestModel) -> None:
        self._model = model

    def build_model(self, model_id: str) -> TestModel:
        assert model_id == "unit-model"
        return self._model

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()


def model_descriptor(*capabilities: Capability) -> ModelDescriptor:
    support = {capability: CapabilitySupport.CONFIGURED for capability in capabilities}
    return ModelDescriptor(provider_id="fake", model_id="unit-model", capabilities=support)


def build_client(model: TestModel, *capabilities: Capability, timeout: float = 1.0) -> AIInferenceClient:
    providers = ProviderRegistry()
    providers.register(FakeProvider(model))
    models = ModelRegistry()
    models.register(model_descriptor(*capabilities))
    router = ModelRouter(providers=providers, models=models, default_provider="fake", default_model="unit-model")
    return AIInferenceClient(
        router=router,
        providers=providers,
        limits=AIClientLimits(timeout_seconds=timeout, max_concurrency=2),
    )


def test_ai_disabled_requires_no_provider_configuration() -> None:
    settings = AISettings(ENABLED=False)

    assert settings.ENABLED is False
    assert settings.DEFAULT_MODEL is None


def test_ai_enabled_requires_default_model() -> None:
    with pytest.raises(ValidationError, match="DEFAULT_MODEL"):
        AISettings(ENABLED=True)


def test_non_https_external_compatible_endpoint_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        AISettings(
            ENABLED=True,
            DEFAULT_PROVIDER="openai_compatible",
            DEFAULT_MODEL="model",
            OPENAI_COMPATIBLE_BASE_URL="http://models.example.com/v1",
            OPENAI_COMPATIBLE_API_KEY=SecretStr("explicit-test-key"),
            ALLOWED_PROVIDERS=("openai_compatible",),
            ALLOWED_ENDPOINT_HOSTS=("models.example.com",),
        )


def test_enabled_compatible_provider_requires_explicit_credentials() -> None:
    with pytest.raises(ValidationError, match="OPENAI_COMPATIBLE_API_KEY"):
        AISettings(
            ENABLED=True,
            DEFAULT_PROVIDER="openai_compatible",
            DEFAULT_MODEL="model",
            OPENAI_COMPATIBLE_BASE_URL="http://127.0.0.1:8080/v1",
            ALLOWED_PROVIDERS=("openai_compatible",),
        )


def test_cloud_compatible_default_requires_cloud_data_policy() -> None:
    with pytest.raises(ValidationError, match="CLOUD_DATA_ALLOWED"):
        AISettings(
            ENABLED=True,
            DEFAULT_PROVIDER="openai_compatible",
            DEFAULT_MODEL="model",
            OPENAI_COMPATIBLE_BASE_URL="https://models.example.com/v1",
            OPENAI_COMPATIBLE_API_KEY=SecretStr("explicit-test-key"),
            OPENAI_COMPATIBLE_IS_CLOUD=True,
            ALLOWED_PROVIDERS=("openai_compatible",),
            ALLOWED_ENDPOINT_HOSTS=("models.example.com",),
        )


def test_provider_and_model_registries_reject_duplicates() -> None:
    providers = ProviderRegistry()
    provider = FakeProvider(TestModel())
    providers.register(provider)
    with pytest.raises(AIConfigurationError, match="already registered"):
        providers.register(provider)

    models = ModelRegistry()
    descriptor = model_descriptor(Capability.TEXT_GENERATION)
    models.register(descriptor)
    with pytest.raises(AIConfigurationError, match="already registered"):
        models.register(descriptor)


def test_router_rejects_unknown_capability_and_silent_cloud_fallback() -> None:
    providers = ProviderRegistry()
    providers.register(FakeProvider(TestModel()))
    models = ModelRegistry()
    models.register(model_descriptor(Capability.TEXT_GENERATION))
    router = ModelRouter(providers=providers, models=models, default_provider="fake", default_model="unit-model")

    with pytest.raises(ModelNotFoundError, match="required capabilities"):
        router.select(required_capabilities={Capability.TOOL_CALLING})

    selected = router.select(
        required_capabilities={Capability.TEXT_GENERATION},
        policy=RoutingPolicy(privacy=PrivacyRequirement.LOCAL_ONLY, allow_cloud_fallback=False),
    )
    assert selected.provider_id == "fake"


@pytest.mark.asyncio
async def test_text_and_structured_inference_use_typed_results() -> None:
    text_client = build_client(
        TestModel(custom_output_text="deterministic"),
        Capability.TEXT_GENERATION,
    )
    text_result = await text_client.generate(AIRequest(prompt="hello"))
    assert text_result.output == "deterministic"
    assert text_result.model.model_id == "unit-model"
    assert text_result.usage.requests == 1

    structured_client = build_client(
        TestModel(custom_output_args={"value": 42}),
        Capability.TEXT_GENERATION,
        Capability.STRUCTURED_OUTPUT,
    )
    structured_result = await structured_client.generate_structured(AIRequest(prompt="answer"), Answer)
    assert structured_result.output == Answer(value=42)


@pytest.mark.asyncio
async def test_streaming_emits_deltas_and_completion_usage() -> None:
    client = build_client(
        TestModel(custom_output_text="streamed"),
        Capability.TEXT_GENERATION,
        Capability.STREAMING,
    )

    events = [event async for event in client.stream(AIRequest(prompt="hello"))]

    assert any(event.kind is StreamEventKind.DELTA and event.delta for event in events)
    assert events[-1].kind is StreamEventKind.COMPLETED
    assert events[-1].usage is not None


@pytest.mark.asyncio
async def test_provider_failures_are_translated_without_prompt_leakage() -> None:
    class BrokenProvider(FakeProvider):
        def build_model(self, model_id: str) -> TestModel:
            raise RuntimeError("provider-secret credential and super-private-prompt")

    providers = ProviderRegistry()
    providers.register(BrokenProvider(TestModel()))
    models = ModelRegistry()
    models.register(model_descriptor(Capability.TEXT_GENERATION))
    router = ModelRouter(providers=providers, models=models, default_provider="fake", default_model="unit-model")
    client = AIInferenceClient(
        router=router,
        providers=providers,
        limits=AIClientLimits(timeout_seconds=1, max_concurrency=1),
    )

    with pytest.raises(AIProviderError) as exc_info:
        await client.generate(AIRequest(prompt="super-private-prompt"))

    assert "super-private-prompt" not in str(exc_info.value)
    assert "credential" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_registry_enforces_permissions_before_model_execution() -> None:
    def read_status() -> str:
        return "ok"

    registry = ToolRegistry()
    registry.register(
        RegisteredTool(
            tool=Tool(read_status, name="read_status"),
            required_permissions=frozenset({"status:read"}),
        )
    )

    with pytest.raises(ToolPermissionDeniedError, match="read_status"):
        registry.resolve({"read_status"}, granted_permissions=frozenset())

    tools = registry.resolve({"read_status"}, granted_permissions=frozenset({"status:read"}))
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_inference_executes_only_explicitly_allowed_tool() -> None:
    calls = 0

    def read_status() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    tool_registry = ToolRegistry()
    tool_registry.register(
        RegisteredTool(
            tool=Tool(read_status, name="read_status"),
            required_permissions=frozenset({"status:read"}),
        )
    )
    base = build_client(
        TestModel(call_tools=["read_status"]),
        Capability.TEXT_GENERATION,
        Capability.TOOL_CALLING,
    )
    client = AIInferenceClient(
        router=base.router,
        providers=base.providers,
        limits=AIClientLimits(timeout_seconds=1, max_concurrency=1),
        dependencies=AIClientDependencies(tool_registry=tool_registry),
    )

    await client.generate(
        AIRequest(
            prompt="read",
            required_capabilities=frozenset({Capability.TOOL_CALLING}),
            allowed_tools=frozenset({"read_status"}),
            granted_tool_permissions=frozenset({"status:read"}),
        )
    )

    assert calls == 1


@pytest.mark.asyncio
async def test_cancellation_is_not_translated_to_provider_error() -> None:
    class BlockingClient(AIInferenceClient):
        async def _run_text(self, request: AIRequest) -> AIResult[str]:
            await asyncio.sleep(60)
            raise AssertionError("request should have been cancelled")

    base = build_client(TestModel(), Capability.TEXT_GENERATION)
    client = BlockingClient(
        router=base.router,
        providers=base.providers,
        limits=AIClientLimits(timeout_seconds=1, max_concurrency=1),
    )
    task = asyncio.create_task(client.generate(AIRequest(prompt="cancel")))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_timeout_is_translated_and_request_limits_are_enforced() -> None:
    class BlockingClient(AIInferenceClient):
        async def _run_text(self, request: AIRequest) -> AIResult[str]:
            await asyncio.sleep(60)
            raise AssertionError("request should have timed out")

    base = build_client(TestModel(), Capability.TEXT_GENERATION)
    client = BlockingClient(
        router=base.router,
        providers=base.providers,
        limits=AIClientLimits(timeout_seconds=0.001, max_concurrency=1, max_input_chars=4),
    )
    with pytest.raises(AIRequestLimitError):
        await client.generate(AIRequest(prompt="too long"))

    client = BlockingClient(
        router=base.router,
        providers=base.providers,
        limits=AIClientLimits(timeout_seconds=0.001, max_concurrency=1),
    )
    with pytest.raises(AIRequestTimeoutError):
        await client.generate(AIRequest(prompt="wait"))


def test_ollama_bootstrap_is_lazy_and_redaction_removes_credentials() -> None:
    client = build_ai_client(
        AISettings(
            ENABLED=True,
            DEFAULT_MODEL="qwen-test",
            DEFAULT_MODEL_CAPABILITIES=(Capability.STREAMING, Capability.STRUCTURED_OUTPUT),
        )
    )
    provider_model = client.providers.get("ollama").build_model("qwen-test")

    assert provider_model.model_name == "qwen-test"
    redacted = redact_sensitive_text("Authorization: Bearer abc.def api_key=sk-private password=hunter2")
    assert "abc.def" not in redacted
    assert "sk-private" not in redacted
    assert "hunter2" not in redacted


@pytest.mark.asyncio
async def test_ollama_discovery_uses_advertised_capabilities_only() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "local-model",
                        "model": "local-model",
                        "capabilities": ["completion", "tools"],
                        "details": {"context_length": 8192},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        provider = OllamaAIProvider(
            ProviderDescriptor("ollama", ProviderLocation.LOCAL, configured=True),
            lambda _model_id: TestModel(),
            base_url="http://127.0.0.1:11434/v1",
            timeout_seconds=1,
            http_client=http_client,
        )
        discovered = await provider.discover_models()

    assert discovered[0].capability(Capability.TEXT_GENERATION) is CapabilitySupport.VERIFIED
    assert discovered[0].capability(Capability.TOOL_CALLING) is CapabilitySupport.VERIFIED
    assert discovered[0].capability(Capability.STRUCTURED_OUTPUT) is CapabilitySupport.UNKNOWN
    assert discovered[0].context_window == 8192


@pytest.mark.asyncio
async def test_observability_records_metadata_without_prompt_or_response() -> None:
    observer = RecordingObserver()
    base = build_client(TestModel(custom_output_text="sensitive-response"), Capability.TEXT_GENERATION)
    client = AIInferenceClient(
        router=base.router,
        providers=base.providers,
        limits=AIClientLimits(timeout_seconds=1, max_concurrency=1),
        dependencies=AIClientDependencies(observer=observer),
    )

    await client.generate(AIRequest(prompt="sensitive-prompt"))

    assert len(observer.events) == 1
    serialized = repr(observer.events[0])
    assert "sensitive-prompt" not in serialized
    assert "sensitive-response" not in serialized
