# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

import pytest
from app.core.core_ai.agents import (
    AgentDefinition,
    AgentRegistry,
    AgentRunContext,
    AgentRuntime,
    RegisteredTool,
    ToolRegistry,
)
from app.core.core_ai.contracts import (
    AIRequest,
    AIResult,
    Capability,
    CapabilitySupport,
    ModelDescriptor,
    ToolApprovalRequiredError,
    ToolPermissionDeniedError,
    Usage,
)
from app.core.core_ai.mcp import MCPServerConfig, MCPServerRegistry
from app.core.core_ai.memory import ConversationMessage, ConversationRole, InMemoryConversationStore
from pydantic_ai import Tool
from pydantic_ai.toolsets import FilteredToolset


class StubInference:
    def __init__(self) -> None:
        self.request: AIRequest | None = None

    async def generate(self, request: AIRequest) -> AIResult[str]:
        self.request = request
        return AIResult(
            output="ok",
            model=ModelDescriptor(
                provider_id="fake",
                model_id="model",
                capabilities={Capability.TEXT_GENERATION: CapabilitySupport.VERIFIED},
            ),
            usage=Usage(requests=1),
        )


@pytest.mark.asyncio
async def test_agent_runtime_applies_registered_tools_permissions_and_limits() -> None:
    inference = StubInference()
    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            agent_id="support",
            instructions="Answer from approved support data.",
            allowed_tools=frozenset({"lookup"}),
            allowed_mcp_servers=frozenset({"docs"}),
        )
    )
    runtime = AgentRuntime(registry=registry, inference=inference)

    result = await runtime.run(
        "support",
        "status",
        context=AgentRunContext(granted_tool_permissions=frozenset({"support:read"}), approved_tools=frozenset()),
    )

    assert result.output == "ok"
    assert inference.request is not None
    assert inference.request.allowed_tools == frozenset({"lookup"})
    assert inference.request.allowed_mcp_servers == frozenset({"docs"})
    assert inference.request.instructions == "Answer from approved support data."


def test_tool_registry_requires_trusted_approval() -> None:
    registry = ToolRegistry()

    def update_record() -> str:
        return "updated"

    registry.register(
        RegisteredTool(
            tool=Tool(update_record, name="update_record"),
            required_permissions=frozenset({"record:write"}),
            requires_approval=True,
        )
    )
    with pytest.raises(ToolApprovalRequiredError):
        registry.resolve(
            {"update_record"},
            granted_permissions=frozenset({"record:write"}),
            approved_tools=frozenset(),
        )


def test_mcp_registry_filters_tools_and_enforces_permissions_without_connecting() -> None:
    registry = MCPServerRegistry(allowed_endpoint_hosts=frozenset({"mcp.example.com"}))
    registry.register(
        MCPServerConfig(
            server_id="docs",
            url="https://mcp.example.com/mcp",
            allowed_tools=frozenset({"search_docs"}),
            required_permissions=frozenset({"docs:read"}),
        )
    )
    with pytest.raises(ToolPermissionDeniedError):
        registry.resolve("docs", granted_permissions=frozenset())

    toolset = registry.resolve("docs", granted_permissions=frozenset({"docs:read"}))
    assert isinstance(toolset, FilteredToolset)


@pytest.mark.asyncio
async def test_conversation_store_is_explicit_and_tenant_isolated() -> None:
    store = InMemoryConversationStore(max_messages_per_conversation=2)
    await store.append("tenant-a", "conversation", ConversationMessage(ConversationRole.USER, "one"))
    await store.append("tenant-a", "conversation", ConversationMessage(ConversationRole.ASSISTANT, "two"))
    await store.append("tenant-a", "conversation", ConversationMessage(ConversationRole.USER, "three"))

    tenant_a = await store.list_messages("tenant-a", "conversation")
    tenant_b = await store.list_messages("tenant-b", "conversation")

    assert [message.content for message in tenant_a] == ["two", "three"]
    assert tenant_b == ()
