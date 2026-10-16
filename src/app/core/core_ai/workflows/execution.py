"""Bounded execution wrapper for Pydantic Graph and compatible runners."""

import asyncio
from typing import Protocol

from app.core.core_ai.contracts import AIConfigurationError, AIRequestTimeoutError, WorkflowExecutionError
from app.core.core_ai.workflows.checkpoints import WorkflowCheckpoint, WorkflowCheckpointStore, WorkflowStatus


class WorkflowRunner[InputT, OutputT](Protocol):
    async def run(self, *, inputs: InputT) -> OutputT: ...


class WorkflowExecutor:
    """Adds timeout, idempotency, and checkpoints without replacing the workflow engine."""

    def __init__(self, *, checkpoints: WorkflowCheckpointStore, timeout_seconds: float) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._checkpoints = checkpoints
        self._timeout_seconds = timeout_seconds

    async def execute[InputT, OutputT](
        self,
        runner: WorkflowRunner[InputT, OutputT],
        *,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        inputs: InputT,
    ) -> OutputT:
        running = WorkflowCheckpoint(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            status=WorkflowStatus.RUNNING,
        )
        if not await self._checkpoints.claim(running):
            current = await self._checkpoints.get(tenant_id, workflow_id, execution_id)
            current_status = current.status.value if current is not None else "claimed"
            raise AIConfigurationError(
                f"Workflow '{workflow_id}' execution '{execution_id}' is already {current_status}"
            )
        try:
            async with asyncio.timeout(self._timeout_seconds):
                output = await runner.run(inputs=inputs)
        except TimeoutError as exc:
            await self._save(tenant_id, workflow_id, execution_id, WorkflowStatus.FAILED, type(exc).__name__)
            raise AIRequestTimeoutError("Workflow execution timed out") from exc
        except asyncio.CancelledError:
            await self._save(tenant_id, workflow_id, execution_id, WorkflowStatus.CANCELLED)
            raise
        except Exception as exc:
            await self._save(tenant_id, workflow_id, execution_id, WorkflowStatus.FAILED, type(exc).__name__)
            raise WorkflowExecutionError("Workflow execution failed") from exc
        await self._save(tenant_id, workflow_id, execution_id, WorkflowStatus.COMPLETED)
        return output

    async def _save(
        self,
        tenant_id: str,
        workflow_id: str,
        execution_id: str,
        status: WorkflowStatus,
        error_type: str | None = None,
    ) -> None:
        await self._checkpoints.save(
            WorkflowCheckpoint(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                status=status,
                error_type=error_type,
            )
        )
