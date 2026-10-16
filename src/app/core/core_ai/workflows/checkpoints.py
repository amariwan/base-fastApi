"""Tenant-isolated workflow checkpoint contracts and in-memory adapter."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WorkflowCheckpoint:
    tenant_id: str
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    error_type: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class WorkflowCheckpointStore(Protocol):
    async def get(self, tenant_id: str, workflow_id: str, execution_id: str) -> WorkflowCheckpoint | None: ...

    async def claim(self, checkpoint: WorkflowCheckpoint) -> bool: ...

    async def save(self, checkpoint: WorkflowCheckpoint) -> None: ...


class InMemoryWorkflowCheckpointStore:
    """Process-local adapter for tests and ephemeral workflow execution."""

    def __init__(self) -> None:
        self._checkpoints: dict[tuple[str, str, str], WorkflowCheckpoint] = {}
        self._lock = asyncio.Lock()

    async def get(self, tenant_id: str, workflow_id: str, execution_id: str) -> WorkflowCheckpoint | None:
        _validate_identity(tenant_id, workflow_id, execution_id)
        async with self._lock:
            return self._checkpoints.get((tenant_id, workflow_id, execution_id))

    async def claim(self, checkpoint: WorkflowCheckpoint) -> bool:
        _validate_identity(checkpoint.tenant_id, checkpoint.workflow_id, checkpoint.execution_id)
        if checkpoint.status is not WorkflowStatus.RUNNING:
            raise ValueError("claimed workflow checkpoints must have running status")
        key = (checkpoint.tenant_id, checkpoint.workflow_id, checkpoint.execution_id)
        async with self._lock:
            current = self._checkpoints.get(key)
            if current is not None and current.status in {WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED}:
                return False
            self._checkpoints[key] = checkpoint
        return True

    async def save(self, checkpoint: WorkflowCheckpoint) -> None:
        _validate_identity(checkpoint.tenant_id, checkpoint.workflow_id, checkpoint.execution_id)
        async with self._lock:
            self._checkpoints[(checkpoint.tenant_id, checkpoint.workflow_id, checkpoint.execution_id)] = checkpoint


def _validate_identity(tenant_id: str, workflow_id: str, execution_id: str) -> None:
    if not tenant_id or not workflow_id or not execution_id:
        raise ValueError("tenant_id, workflow_id, and execution_id are required")
