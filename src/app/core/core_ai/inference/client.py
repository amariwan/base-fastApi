"""Unified text, structured-output, and streaming inference client."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from app.core.core_ai.agents import ToolRegistry
from app.core.core_ai.contracts import (
    AIOutputValidationError,
    AIProviderError,
    AIRequest,
    AIRequestLimitError,
    AIRequestTimeoutError,
    AIResult,
    Capability,
    ModelDescriptor,
    PrivacyRequirement,
    StreamEvent,
    StreamEventKind,
    Usage,
)
from app.core.core_ai.inference.router import ModelRouter, RoutingPolicy
from app.core.core_ai.mcp import MCPServerRegistry
from app.core.core_ai.observability import AIEvent, AIObserver, NullAIObserver
from app.core.core_ai.observability.usage import usage_from_run
from app.core.core_ai.registry import ProviderRegistry
from app.core.core_ai.security.limits import AIClientLimits
from pydantic import BaseModel
from pydantic_ai import Agent, Tool, UsageLimits
from pydantic_ai.models.instrumented import InstrumentationSettings, InstrumentedModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.toolsets import AbstractToolset

OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class AIClientDependencies:
    tool_registry: ToolRegistry | None = None
    mcp_registry: MCPServerRegistry | None = None
    observer: AIObserver = NullAIObserver()
    instrumentation_enabled: bool = False


class AIInferenceClient:
    def __init__(
        self,
        *,
        router: ModelRouter,
        providers: ProviderRegistry,
        limits: AIClientLimits,
        dependencies: AIClientDependencies | None = None,
    ) -> None:
        self.router = router
        self.providers = providers
        self._limits = limits
        self._semaphore = asyncio.Semaphore(limits.max_concurrency)
        resolved_dependencies = dependencies or AIClientDependencies()
        self._tool_registry = resolved_dependencies.tool_registry
        self._mcp_registry = resolved_dependencies.mcp_registry
        self._observer = resolved_dependencies.observer
        self._instrumentation_enabled = resolved_dependencies.instrumentation_enabled
        self._logger = logging.getLogger("app_logger")

    async def generate(self, request: AIRequest) -> AIResult[str]:
        self._validate_request(request)
        started = time.monotonic()
        try:
            async with self._semaphore, asyncio.timeout(self._limits.timeout_seconds):
                result = await self._run_text(request)
        except TimeoutError as exc:
            self._record_failure("generate", request, started, AIRequestTimeoutError)
            raise AIRequestTimeoutError("AI provider request timed out") from exc
        except asyncio.CancelledError:
            self._record_failure("generate", request, started, asyncio.CancelledError)
            raise
        except AIProviderError as exc:
            self._record_failure("generate", request, started, type(exc))
            raise
        except Exception as exc:
            self._record_failure("generate", request, started, type(exc))
            raise AIProviderError("AI provider request failed") from exc
        self._record_success("generate", result, started)
        return result

    async def _run_text(self, request: AIRequest) -> AIResult[str]:
        descriptor, agent = self._build_agent(request, output_type=str, extra_capabilities=frozenset())
        result = await agent.run(
            request.prompt,
            usage_limits=self._usage_limits(request),
            model_settings=self._model_settings(request),
        )
        if not isinstance(result.output, str):
            raise AIOutputValidationError("AI provider returned a non-text result")
        return AIResult(output=result.output, model=descriptor, usage=self._usage(result.usage))

    async def generate_structured(self, request: AIRequest, output_type: type[OutputModelT]) -> AIResult[OutputModelT]:
        self._validate_request(request)
        started = time.monotonic()
        try:
            async with self._semaphore, asyncio.timeout(self._limits.timeout_seconds):
                descriptor, agent = self._build_agent(
                    request,
                    output_type=output_type,
                    extra_capabilities=frozenset({Capability.STRUCTURED_OUTPUT}),
                )
                result = await agent.run(
                    request.prompt,
                    usage_limits=self._usage_limits(request),
                    model_settings=self._model_settings(request),
                )
                if not isinstance(result.output, output_type):
                    raise AIOutputValidationError("AI provider returned an invalid structured result")
                typed_result = AIResult(output=result.output, model=descriptor, usage=self._usage(result.usage))
        except TimeoutError as exc:
            self._record_failure("generate_structured", request, started, AIRequestTimeoutError)
            raise AIRequestTimeoutError("AI provider request timed out") from exc
        except asyncio.CancelledError:
            self._record_failure("generate_structured", request, started, asyncio.CancelledError)
            raise
        except AIOutputValidationError as exc:
            self._record_failure("generate_structured", request, started, type(exc))
            raise
        except Exception as exc:
            self._record_failure("generate_structured", request, started, type(exc))
            raise AIOutputValidationError("AI provider could not produce the requested structured output") from exc
        self._record_success("generate_structured", typed_result, started)
        return typed_result

    async def stream(self, request: AIRequest) -> AsyncIterator[StreamEvent]:
        self._validate_request(request)
        started = time.monotonic()
        try:
            async with self._semaphore, asyncio.timeout(self._limits.timeout_seconds):
                descriptor, agent = self._build_agent(
                    request,
                    output_type=str,
                    extra_capabilities=frozenset({Capability.STREAMING}),
                )
                async with agent.run_stream(
                    request.prompt,
                    usage_limits=self._usage_limits(request),
                    model_settings=self._model_settings(request),
                ) as result:
                    async for delta in result.stream_text(delta=True):
                        if delta:
                            yield StreamEvent(kind=StreamEventKind.DELTA, delta=delta)
                    usage = self._usage(result.usage)
                    yield StreamEvent(kind=StreamEventKind.COMPLETED, usage=usage)
                    self._notify(
                        AIEvent(
                            operation="stream",
                            success=True,
                            duration_seconds=time.monotonic() - started,
                            provider_id=descriptor.provider_id,
                            model_id=descriptor.model_id,
                            usage=usage,
                        )
                    )
        except TimeoutError as exc:
            self._record_failure("stream", request, started, AIRequestTimeoutError)
            raise AIRequestTimeoutError("AI provider stream timed out") from exc
        except asyncio.CancelledError:
            self._record_failure("stream", request, started, asyncio.CancelledError)
            raise
        except AIProviderError as exc:
            self._record_failure("stream", request, started, type(exc))
            raise
        except Exception as exc:
            self._record_failure("stream", request, started, type(exc))
            raise AIProviderError("AI provider stream failed") from exc

    def _build_agent(
        self,
        request: AIRequest,
        *,
        output_type: type[Any],
        extra_capabilities: frozenset[Capability],
    ) -> tuple[ModelDescriptor, Agent[Any, Any]]:
        required = set(request.required_capabilities)
        required.add(Capability.TEXT_GENERATION)
        required.update(extra_capabilities)
        descriptor = self.router.select(
            required_capabilities=required,
            provider_id=request.provider_id,
            model_id=request.model_id,
            policy=RoutingPolicy(
                privacy=request.privacy,
                allow_cloud_fallback=request.allow_cloud_fallback and self._limits.cloud_fallback_enabled,
            ),
        )
        provider = self.providers.get(descriptor.provider_id)
        model = provider.build_model(descriptor.model_id)
        if self._instrumentation_enabled:
            model = InstrumentedModel(
                model,
                options=InstrumentationSettings(
                    include_content=False,
                    include_binary_content=False,
                    include_model_request_parameters=False,
                ),
            )
        tools = self._resolve_tools(request)
        agent = Agent(
            model,
            output_type=output_type,
            system_prompt=request.system_prompt or (),
            instructions=request.instructions,
            retries=request.parameters.retries,
            tools=tools,
            toolsets=self._resolve_mcp_toolsets(request),
        )
        return descriptor, agent

    def _resolve_tools(self, request: AIRequest) -> Sequence[Tool[Any]]:
        if not request.allowed_tools:
            return ()
        if self._tool_registry is None:
            raise AIProviderError("AI tools were requested but no tool registry is configured")
        return self._tool_registry.resolve(
            request.allowed_tools,
            granted_permissions=request.granted_tool_permissions,
            approved_tools=request.approved_tools,
        )

    def _resolve_mcp_toolsets(self, request: AIRequest) -> Sequence[AbstractToolset[object]]:
        if not request.allowed_mcp_servers:
            return ()
        if self._mcp_registry is None:
            raise AIProviderError("MCP servers were requested but no MCP registry is configured")
        return self._mcp_registry.resolve_many(
            request.allowed_mcp_servers,
            granted_permissions=request.granted_tool_permissions,
        )

    def _validate_request(self, request: AIRequest) -> None:
        if request.privacy is PrivacyRequirement.CLOUD_ALLOWED and not self._limits.cloud_data_allowed:
            raise AIRequestLimitError("Cloud data transmission is disabled by deployment policy")
        if len(request.prompt) > self._limits.max_input_chars:
            raise AIRequestLimitError("AI prompt exceeds the configured character limit")
        requested_output_tokens = request.parameters.max_output_tokens
        if requested_output_tokens is not None and requested_output_tokens > self._limits.max_output_tokens:
            raise AIRequestLimitError("AI output token limit exceeds the configured maximum")
        if request.limits.tool_calls_limit > self._limits.max_tool_calls:
            raise AIRequestLimitError("AI tool-call limit exceeds the configured maximum")
        if request.limits.request_limit > self._limits.max_model_requests:
            raise AIRequestLimitError("AI model-request limit exceeds the configured maximum")

    def _record_success(self, operation: str, result: AIResult[Any], started: float) -> None:
        self._notify(
            AIEvent(
                operation=operation,
                success=True,
                duration_seconds=time.monotonic() - started,
                provider_id=result.model.provider_id,
                model_id=result.model.model_id,
                usage=result.usage,
            )
        )

    def _record_failure(
        self,
        operation: str,
        request: AIRequest,
        started: float,
        error_type: type[BaseException],
    ) -> None:
        self._notify(
            AIEvent(
                operation=operation,
                success=False,
                duration_seconds=time.monotonic() - started,
                provider_id=request.provider_id,
                model_id=request.model_id,
                error_type=error_type.__name__,
            )
        )

    def _notify(self, event: AIEvent) -> None:
        try:
            self._observer.record(event)
        except Exception:
            self._logger.exception("AI observer failed")

    @staticmethod
    def _model_settings(request: AIRequest) -> ModelSettings:
        settings: ModelSettings = {}
        if request.parameters.temperature is not None:
            settings["temperature"] = request.parameters.temperature
        if request.parameters.max_output_tokens is not None:
            settings["max_tokens"] = request.parameters.max_output_tokens
        if request.parameters.seed is not None:
            settings["seed"] = request.parameters.seed
        return settings

    @staticmethod
    def _usage_limits(request: AIRequest) -> UsageLimits:
        return UsageLimits(
            request_limit=request.limits.request_limit,
            tool_calls_limit=request.limits.tool_calls_limit,
            input_tokens_limit=request.limits.input_tokens_limit,
            output_tokens_limit=request.limits.output_tokens_limit,
            total_tokens_limit=request.limits.total_tokens_limit,
        )

    @staticmethod
    def _usage(run_usage: Any) -> Usage:
        return usage_from_run(run_usage)
