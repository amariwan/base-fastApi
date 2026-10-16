# Ruff's repository test ignore glob does not match co-located src/app tests.
# ruff: noqa: S101

import asyncio

import pytest
from app.core.core_ai.contracts import AIConfigurationError, AIRequestTimeoutError, WorkflowExecutionError
from app.core.core_ai.workflows import InMemoryWorkflowCheckpointStore, WorkflowExecutor, WorkflowStatus


class StubRunner:
    def __init__(self, *, result: str = "done", error: Exception | None = None, delay: float = 0) -> None:
        self.result = result
        self.error = error
        self.delay = delay

    async def run(self, *, inputs: str) -> str:
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return f"{inputs}:{self.result}"


@pytest.mark.asyncio
async def test_workflow_executor_checkpoints_success_and_rejects_duplicate() -> None:
    store = InMemoryWorkflowCheckpointStore()
    executor = WorkflowExecutor(checkpoints=store, timeout_seconds=1)

    result = await executor.execute(
        StubRunner(),
        tenant_id="tenant-a",
        workflow_id="classify",
        execution_id="run-1",
        inputs="document",
    )

    assert result == "document:done"
    checkpoint = await store.get("tenant-a", "classify", "run-1")
    assert checkpoint is not None
    assert checkpoint.status is WorkflowStatus.COMPLETED
    with pytest.raises(AIConfigurationError, match="already completed"):
        await executor.execute(
            StubRunner(),
            tenant_id="tenant-a",
            workflow_id="classify",
            execution_id="run-1",
            inputs="document",
        )


@pytest.mark.asyncio
async def test_workflow_executor_records_failure_without_leaking_message() -> None:
    store = InMemoryWorkflowCheckpointStore()
    executor = WorkflowExecutor(checkpoints=store, timeout_seconds=1)

    with pytest.raises(WorkflowExecutionError, match="Workflow execution failed"):
        await executor.execute(
            StubRunner(error=RuntimeError("secret provider payload")),
            tenant_id="tenant-a",
            workflow_id="classify",
            execution_id="run-2",
            inputs="document",
        )

    checkpoint = await store.get("tenant-a", "classify", "run-2")
    assert checkpoint is not None
    assert checkpoint.status is WorkflowStatus.FAILED
    assert checkpoint.error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_workflow_executor_enforces_timeout() -> None:
    store = InMemoryWorkflowCheckpointStore()
    executor = WorkflowExecutor(checkpoints=store, timeout_seconds=0.001)

    with pytest.raises(AIRequestTimeoutError):
        await executor.execute(
            StubRunner(delay=0.05),
            tenant_id="tenant-a",
            workflow_id="classify",
            execution_id="run-3",
            inputs="document",
        )

    checkpoint = await store.get("tenant-a", "classify", "run-3")
    assert checkpoint is not None
    assert checkpoint.status is WorkflowStatus.FAILED


@pytest.mark.asyncio
async def test_workflow_executor_claim_is_atomic_for_concurrent_execution() -> None:
    store = InMemoryWorkflowCheckpointStore()
    executor = WorkflowExecutor(checkpoints=store, timeout_seconds=1)
    runner = StubRunner(delay=0.01)

    results = await asyncio.gather(
        executor.execute(
            runner,
            tenant_id="tenant-a",
            workflow_id="classify",
            execution_id="same-run",
            inputs="first",
        ),
        executor.execute(
            runner,
            tenant_id="tenant-a",
            workflow_id="classify",
            execution_id="same-run",
            inputs="second",
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(result, AIConfigurationError) for result in results) == 1
    assert sum(isinstance(result, str) for result in results) == 1
