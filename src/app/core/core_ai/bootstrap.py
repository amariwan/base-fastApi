"""Lazy Core AI composition root."""

from functools import lru_cache, partial

from app.core.core_ai.agents import ToolRegistry
from app.core.core_ai.config import AISettings, get_ai_settings
from app.core.core_ai.contracts import (
    AIConfigurationError,
    AIDisabledError,
    Capability,
    CapabilitySupport,
    ModelDescriptor,
    ProviderDescriptor,
    ProviderLocation,
)
from app.core.core_ai.inference import AIClientDependencies, AIClientLimits, AIInferenceClient, ModelRouter
from app.core.core_ai.integrations import OllamaAIProvider, PydanticAIProvider
from app.core.core_ai.integrations.cloud import cloud_model_factory
from app.core.core_ai.integrations.openai_compatible import build_openai_compatible_model
from app.core.core_ai.mcp import MCPServerRegistry
from app.core.core_ai.observability import LoggingAIObserver, NullAIObserver
from app.core.core_ai.registry import ModelRegistry, ProviderRegistry
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider


def _secret(settings_value: object) -> str | None:
    get_secret_value = getattr(settings_value, "get_secret_value", None)
    if callable(get_secret_value):
        value = str(get_secret_value()).strip()
        return value or None
    return None


def _register_providers(settings: AISettings, registry: ProviderRegistry) -> None:
    allowed = set(settings.ALLOWED_PROVIDERS)

    if "ollama" in allowed:
        registry.register(
            OllamaAIProvider(
                ProviderDescriptor("ollama", ProviderLocation.LOCAL, configured=True),
                lambda model_id: OllamaModel(model_id, provider=OllamaProvider(base_url=settings.OLLAMA_BASE_URL)),
                base_url=settings.OLLAMA_BASE_URL,
                timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            )
        )

    if "openai_compatible" in allowed:
        api_key = _secret(settings.OPENAI_COMPATIBLE_API_KEY)
        base_url = settings.OPENAI_COMPATIBLE_BASE_URL
        configured = base_url is not None and api_key is not None
        location = ProviderLocation.CLOUD if settings.OPENAI_COMPATIBLE_IS_CLOUD else ProviderLocation.LOCAL
        compatible_factory = None
        if base_url is not None and api_key is not None:
            compatible_factory = partial(build_openai_compatible_model, base_url=base_url, api_key=api_key)

        registry.register(
            PydanticAIProvider(ProviderDescriptor("openai_compatible", location, configured), compatible_factory)
        )

    cloud_specs: tuple[tuple[str, str | None], ...] = (
        ("openai", _secret(settings.OPENAI_API_KEY)),
        ("anthropic", _secret(settings.ANTHROPIC_API_KEY)),
        ("google", _secret(settings.GOOGLE_API_KEY)),
        ("openrouter", _secret(settings.OPENROUTER_API_KEY)),
    )
    for provider_id, api_key in cloud_specs:
        if provider_id not in allowed:
            continue
        factory = cloud_model_factory(provider_id, api_key) if api_key else None
        registry.register(
            PydanticAIProvider(
                ProviderDescriptor(provider_id, ProviderLocation.CLOUD, configured=api_key is not None),
                factory,
            )
        )


def _register_models(settings: AISettings, registry: ModelRegistry) -> None:
    configured_models = {provider: list(model_ids) for provider, model_ids in settings.MODELS.items()}
    if settings.DEFAULT_MODEL:
        configured_models.setdefault(settings.DEFAULT_PROVIDER, [])
        if settings.DEFAULT_MODEL not in configured_models[settings.DEFAULT_PROVIDER]:
            configured_models[settings.DEFAULT_PROVIDER].append(settings.DEFAULT_MODEL)

    for provider_id, model_ids in configured_models.items():
        for model_id in model_ids:
            capabilities: dict[Capability, CapabilitySupport] = {
                Capability.TEXT_GENERATION: CapabilitySupport.CONFIGURED
            }
            if provider_id == settings.DEFAULT_PROVIDER and model_id == settings.DEFAULT_MODEL:
                capabilities.update(
                    {capability: CapabilitySupport.CONFIGURED for capability in settings.DEFAULT_MODEL_CAPABILITIES}
                )
            registry.register(
                ModelDescriptor(
                    provider_id=provider_id,
                    model_id=model_id,
                    capabilities=capabilities,
                )
            )


def build_ai_client(
    settings: AISettings,
    *,
    tool_registry: ToolRegistry | None = None,
    mcp_registry: MCPServerRegistry | None = None,
) -> AIInferenceClient:
    if not settings.ENABLED:
        raise AIDisabledError("AI capabilities are disabled")
    if settings.DEFAULT_MODEL is None:
        raise AIConfigurationError("A default AI model is required")

    providers = ProviderRegistry()
    models = ModelRegistry()
    _register_providers(settings, providers)
    _register_models(settings, models)
    router = ModelRouter(
        providers=providers,
        models=models,
        default_provider=settings.DEFAULT_PROVIDER,
        default_model=settings.DEFAULT_MODEL,
    )
    return AIInferenceClient(
        router=router,
        providers=providers,
        dependencies=AIClientDependencies(
            tool_registry=tool_registry,
            mcp_registry=mcp_registry,
            observer=LoggingAIObserver() if settings.TRACING_ENABLED else NullAIObserver(),
            instrumentation_enabled=settings.TRACING_ENABLED,
        ),
        limits=AIClientLimits(
            timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS,
            max_concurrency=settings.MAX_CONCURRENT_REQUESTS,
            max_input_chars=settings.MAX_INPUT_CHARS,
            max_output_tokens=settings.MAX_OUTPUT_TOKENS,
            max_tool_calls=settings.MAX_TOOL_CALLS,
            max_model_requests=settings.MAX_MODEL_REQUESTS,
            cloud_data_allowed=settings.CLOUD_DATA_ALLOWED,
            cloud_fallback_enabled=settings.CLOUD_FALLBACK_ENABLED,
        ),
    )


@lru_cache(maxsize=1)
def get_ai_client() -> AIInferenceClient:
    return build_ai_client(get_ai_settings())


def reset_ai_client() -> None:
    get_ai_client.cache_clear()
