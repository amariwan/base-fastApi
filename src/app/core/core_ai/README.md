# Core AI

`app.core.core_ai` is the backend's optional AI platform. It centralizes provider
construction, model metadata and routing, inference, embeddings, retrieval,
agent execution controls, MCP clients, optional conversation history, safe
telemetry, and deterministic evaluations. It exposes internal Python APIs; it
does not register an HTTP router.

## 1. Architecture overview

```text
business application port
        ^
business infrastructure adapter
        |
AgentRuntime / AIInferenceClient
        |
ModelRouter -> ModelRegistry + ProviderRegistry
        |
PydanticAI model -> Ollama / OpenAI-compatible / cloud provider
```

The implementation is split by responsibility; package `__init__.py` files are
the stable import surface:

```text
core_ai/
├── contracts/       # public values, events, protocols, exceptions
├── registry/        # provider and model registration
├── inference/       # client and capability-aware routing
├── integrations/    # PydanticAI, Ollama, compatible and cloud adapters
├── embeddings/      # model registry and bounded embedding service
├── knowledge/       # chunking, ingestion, retrieval, vector-store port
├── agents/          # definitions, runtime, tools, permissions, approvals
├── workflows/       # bounded execution and optional checkpoints
├── mcp/             # lazy clients, registry and endpoint security
├── memory/          # conversation values, history policy and storage port
├── security/        # endpoint policy, limits and redaction
├── observability/   # tracing, metrics, usage and evaluations
└── tests/            # unit, opt-in integration and architecture tests
```

Business Application and Domain layers must not import `core_ai` or PydanticAI.
A business Infrastructure adapter implements the service-owned Application port
using this module. Provider construction is lazy and performs no import-time
network request.

## 2. Supported capabilities

Implemented and offline-tested:

- text generation and typed Pydantic output;
- async text streaming, cancellation, deadlines, concurrency and usage limits;
- explicit provider/model registries and capability-aware routing;
- Ollama, generic OpenAI-compatible, OpenAI, Anthropic, Google, and OpenRouter
  model construction;
- controlled PydanticAI tools with permissions and trusted pre-approval;
- embeddings, deterministic chunking, tenant-aware vector search, ingestion,
  and retrieval;
- reusable agent definitions and bounded execution contexts;
- lazy HTTP MCP toolsets with endpoint, permission, and tool allowlists;
- opt-in bounded conversation history;
- bounded workflow execution with idempotency and tenant-aware checkpoints;
- prompt-free operational events, aggregate metrics, usage normalization, and
  Pydantic Evals exact-match datasets.

Not claimed by this implementation: a persistent pgvector adapter, model
reranker, persistent conversation/checkpoint repository, scheduler, or P3
multi-agent/multimodal orchestration. Add these only for a concrete service
requirement.

## 3. Provider configuration

AI is disabled by default. The application starts without credentials because
`get_ai_client()` is only evaluated when an AI-enabled adapter requests it.

```dotenv
AI_ENABLED=false
AI_DEFAULT_PROVIDER=ollama
AI_DEFAULT_MODEL=
AI_DEFAULT_MODEL_CAPABILITIES=streaming,structured_output,tool_calling
AI_ALLOWED_PROVIDERS=ollama
AI_ALLOWED_ENDPOINT_HOSTS=
AI_CLOUD_DATA_ALLOWED=false
AI_CLOUD_FALLBACK_ENABLED=false
AI_REQUEST_TIMEOUT_SECONDS=60
AI_MAX_CONCURRENT_REQUESTS=4
AI_MAX_INPUT_CHARS=200000
AI_MAX_OUTPUT_TOKENS=4096
AI_MAX_TOOL_CALLS=8
AI_MAX_MODEL_REQUESTS=3
AI_STORE_PROMPTS=false
AI_STORE_RESPONSES=false
AI_TRACING_ENABLED=false
```

Capabilities are never inferred from a model name. Declare only capabilities
verified for the configured deployment. Unknown capabilities stay unknown and
cannot satisfy routing requirements.

`AI_MODELS` accepts a JSON mapping for additional registered models, for
example `{"ollama":["qwen3"],"openai":["deployment-name"]}`.

## 4. Local Ollama setup

```dotenv
AI_ENABLED=true
AI_DEFAULT_PROVIDER=ollama
AI_DEFAULT_MODEL=qwen3
AI_DEFAULT_MODEL_CAPABILITIES=streaming,structured_output,tool_calling
AI_ALLOWED_PROVIDERS=ollama
AI_OLLAMA_BASE_URL=http://localhost:11434/v1
```

The URL must be local/private unless its host is explicitly allowlisted. Model
construction is lazy; configuration does not prove that Ollama or the model is
currently available.

## 5. OpenAI-compatible setup

Use one shared adapter for llama.cpp, vLLM, MLX-compatible servers, and other
compatible Chat Completions endpoints:

```dotenv
AI_ENABLED=true
AI_DEFAULT_PROVIDER=openai_compatible
AI_DEFAULT_MODEL=my-deployment
AI_ALLOWED_PROVIDERS=openai_compatible
AI_OPENAI_COMPATIBLE_BASE_URL=http://127.0.0.1:8080/v1
AI_OPENAI_COMPATIBLE_API_KEY=server-configured-value
AI_OPENAI_COMPATIBLE_IS_CLOUD=false
```

The OpenAI client requires an explicit compatible-server key, including when a
local server treats it as a non-secret placeholder; Core AI never substitutes
an ambient cloud credential. External hosts require HTTPS and
`AI_ALLOWED_ENDPOINT_HOSTS`. Set
`AI_OPENAI_COMPATIBLE_IS_CLOUD=true` and `AI_CLOUD_DATA_ALLOWED=true` when the
endpoint transmits data off the trusted local/private network.

## 6. Optional cloud providers

Cloud providers are opt-in and require both allowlisting and credentials:

```dotenv
AI_ALLOWED_PROVIDERS=ollama,openai,anthropic,google,openrouter
AI_CLOUD_DATA_ALLOWED=true
AI_OPENAI_API_KEY=
AI_ANTHROPIC_API_KEY=
AI_GOOGLE_API_KEY=
AI_OPENROUTER_API_KEY=
```

There is no silent cloud fallback. A request must permit cloud data and either
select a cloud provider explicitly or use an explicitly enabled fallback
policy.

## 7. Model registry and routing

`ModelDescriptor` stores provider/model identity, tri-state capability evidence,
known token windows, and optional cost data. Unknown values remain `None` or
`CapabilitySupport.UNKNOWN`; the platform does not invent pricing or context
windows. `ModelRouter` first evaluates an explicit/default model and only
evaluates alternatives when the request policy allows fallback.

Ollama `discover_models()` calls its local `/api/tags` endpoint on demand and
marks only advertised capabilities as verified. Other providers deliberately
return an empty result where there is no portable authoritative listing API;
static configuration remains their source of truth.

## 8. Text inference

```python
from app.core.core_ai import AIRequest, get_ai_client

client = get_ai_client()
result = await client.generate(AIRequest(prompt="Summarize the incident."))
print(result.output, result.usage)
```

The client translates provider failures to secret-safe Core AI exceptions and
preserves the original exception as `__cause__` for trusted diagnostics.

## 9. Structured output

```python
from pydantic import BaseModel
from app.core.core_ai import AIRequest, Capability, get_ai_client


class Classification(BaseModel):
    label: str
    confidence: float


request = AIRequest(
    prompt="Classify this text",
    required_capabilities=frozenset({Capability.STRUCTURED_OUTPUT}),
)
result = await get_ai_client().generate_structured(request, Classification)
```

PydanticAI performs provider interaction and output validation. Invalid or
exhausted output retries raise `AIOutputValidationError`; partial invalid data
is not returned as success.

## 10. Streaming

```python
async for event in get_ai_client().stream(AIRequest(prompt="Explain the result")):
    if event.delta:
        consume(event.delta)
```

The final event contains usage. Cancellation propagates, and timeout/cancellation
closes the PydanticAI streaming context. Core AI does not define an HTTP/SSE
wire protocol; an owning service API adapter chooses that transport.

## 11. Embeddings and retrieval

`EmbeddingService` wraps PydanticAI embedding models with batch validation and
timeouts. `VectorStore` is the persistence port. `InMemoryVectorStore` is an
actual process-local adapter for tests or ephemeral use and always requires a
trusted tenant ID.

`KnowledgeIngestor` performs deterministic character chunking, embeddings, and
upserts. `KnowledgeRetriever` embeds the query and performs filtered similarity
search. Product-specific extraction, authorization, metadata semantics, and
prompt assembly remain in the business service.

PostgreSQL is already present, so a future persistent adapter should prefer a
reviewed pgvector migration over adding another mandatory vector service. No
schema change is included here.

## 12. Agent creation

```python
definition = AgentDefinition(
    agent_id="document_assistant",
    instructions="Use only approved document tools.",
    allowed_tools=frozenset({"find_document"}),
)
registry.register(definition)
result = await AgentRuntime(registry=registry, inference=client).run(
    "document_assistant",
    "Find the policy",
    context=AgentRunContext(
        granted_tool_permissions=frozenset({"documents:read"}),
    ),
)
```

Definitions contain reusable technical execution configuration, not
business-specific agents shipped by Core.

## 13. Tool permissions and approvals

`ToolRegistry` accepts PydanticAI `Tool` instances. Every run supplies an
explicit tool allowlist and trusted permissions. Tools marked
`requires_approval=True` additionally require their name in
`AIRequest.approved_tools`; model text cannot grant approval. Do not register
shell execution, unrestricted filesystem access, or ambient production
credentials.

## 14. MCP integration

`MCPServerRegistry` accepts only HTTP(S) servers with an explicit endpoint-host
policy and a non-empty tool allowlist. `resolve()` checks trusted permissions
before returning a lazy `FilteredToolset`. Server instructions, sampling, and
elicitation are disabled by default. The PydanticAI/FastMCP context owns
connection startup and cleanup.

## 15. Memory and workflows

Conversation storage is opt-in. `InMemoryConversationStore` is bounded and
tenant-isolated; nothing calls it automatically, and prompt/response persistence
settings default to false.

`WorkflowExecutor` wraps Pydantic Graph or another compatible async runner with
a timeout, cancellation propagation, idempotent execution IDs, and checkpoint
status. `InMemoryWorkflowCheckpointStore` is intended for tests or ephemeral
execution; durable resumability requires a service-owned persistence adapter.
The Core does not ship a competing graph engine or scheduler. Use the existing
job port for scheduling and define rollback semantics before enabling durable
resumable execution.

## 16. Observability

`AIEvent` contains operation, provider/model identity, duration, usage, success,
and error type. It never contains prompts, responses, credentials, tool
arguments, or retrieved documents. `LoggingAIObserver` uses the existing
`app_logger`. With `AI_TRACING_ENABLED=true`, models are wrapped in PydanticAI's
OpenTelemetry instrumentation at lazy composition time with prompt, response,
binary content, and model request parameters disabled. Exporters remain owned
by the application; imports never configure global telemetry.

Cost is emitted only when the provider returns reliable cost metadata. Unknown
cost remains `None`.

## 17. Evaluations and testing

`exact_match_dataset()` creates deterministic Pydantic Evals datasets suitable
for CI. Unit tests use PydanticAI `TestModel` and `TestEmbeddingModel`, so normal
test execution needs no credentials or model server.

```bash
uv run pytest -q src/app/core/core_ai/tests
uv run ruff check src/app/core/core_ai
uv run mypy src/app/core/core_ai
```

Live Ollama/cloud/MCP tests must be separately marked integration tests and must
not make offline CI fail when infrastructure is absent.

## 18. Security and privacy

- AI, cloud transmission, cloud fallback, prompt storage, and response storage
  default to disabled.
- External custom and MCP endpoints require HTTPS plus an explicit host
  allowlist; local/private endpoints may use HTTP.
- Request characters, output tokens, model requests, tool calls, concurrency,
  and deadlines are bounded.
- Tool permissions and approval are enforced before model execution.
- Model output, retrieved content, and MCP metadata are untrusted input.
- Redaction helpers and telemetry exclude common secrets and content by default.
- Tenant IDs must come from trusted auth/application context, never from model
  output.

## 19. Troubleshooting

- `AIDisabledError`: set `AI_ENABLED=true` only for an AI-enabled deployment.
- `AI_DEFAULT_MODEL is required`: configure a concrete deployed model name.
- `No available model satisfies required capabilities`: declare only verified
  model capabilities or choose a compatible model.
- endpoint validation failure: use a private/local host or HTTPS plus
  `AI_ALLOWED_ENDPOINT_HOSTS`.
- provider failure: inspect the chained exception in trusted logs; the public
  Core AI message intentionally omits provider payloads and secrets.
- Ollama connection failure: verify the server separately at the configured
  base URL and confirm the model is pulled.

## 20. Extension guidance for business services

Define a service-owned Application port and implement it in Infrastructure:

```python
# services/documents/application/ports/classifier.py
class DocumentClassifier(Protocol):
    async def classify(self, text: str) -> Classification: ...


# services/documents/infrastructure/ai/core_ai_classifier.py
class CoreAIDocumentClassifier:
    def __init__(self, client: AIInferenceClient) -> None:
        self._client = client

    async def classify(self, text: str) -> Classification:
        result = await self._client.generate_structured(AIRequest(prompt=text), Classification)
        return result.output
```

Keep prompts, business permissions, RAG filters, and service-specific agents in
the owning service. Add provider capabilities only with documented evidence and
tests. Add lifecycle hooks only when a concrete resource must be opened and
closed; the current adapters require none.

