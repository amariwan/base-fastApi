"""Shared async job management interfaces and domain models.

This module provides port (interface) definitions for async job management,
allowing multiple services (docgen, docmanager, etc.) to implement job stores
with different backends (in-memory, database, redis) while maintaining a
consistent contract.

Ports:
  - JobStorePort: abstract interface for job state management

Models:
  - JobInfo: immutable job metadata
  - JobStatus: job lifecycle states

Exceptions:
  - JobNotFoundError, JobExpiredError, JobAlreadyCompletedError: domain errors
"""

from .exceptions import JobAlreadyCompletedError, JobExpiredError, JobNotFoundError
from .models import JobInfo, JobStatus
from .ports import JobStorePort

__all__ = [
    "JobStorePort",
    "JobInfo",
    "JobStatus",
    "JobNotFoundError",
    "JobExpiredError",
    "JobAlreadyCompletedError",
]
