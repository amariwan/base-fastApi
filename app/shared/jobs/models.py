"""Job domain models and enums."""

from dataclasses import dataclass, field
from enum import StrEnum
from time import time


class JobStatus(StrEnum):
    """Job lifecycle states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class JobInfo:
    """Immutable job metadata.

    Attributes:
        status: Current lifecycle state
        created_at: Unix timestamp of job creation
        expires_at: Unix timestamp when job expires (optional)
        document_id: External identifier of persisted result (e.g., storage ID)
        size: Size of result in bytes
        error: Error message if status is FAILED
    """

    status: JobStatus
    created_at: float = field(default_factory=time)
    expires_at: float | None = None
    document_id: str | None = None
    size: int | None = None
    error: str | None = None
    download_token: str | None = None

    def is_expired(self) -> bool:
        """Check if job has expired based on expires_at timestamp."""
        if self.expires_at is None:
            return False
        return time() > self.expires_at

    def is_completed(self) -> bool:
        """Check if job is in terminal state (DONE or FAILED)."""
        return self.status in (JobStatus.DONE, JobStatus.FAILED)
