"""Port (interface) for async job state management.

This module defines the abstract interface that job store implementations
must provide. Multiple services can implement this port with different
backends (in-memory, database, redis, etc.).

Example Usage:
  from app.shared.jobs import JobStorePort, JobInfo, JobStatus

    class InMemoryJobStore(JobStorePort):
            ...

    job_store: JobStorePort = InMemoryJobStore()

  # Create a pending job
  job_info = await job_store.create_job("job-123")
  assert job_info.status == JobStatus.PENDING

  # Transition to running
  await job_store.mark_running("job-123")

  # Complete with result
  await job_store.complete("job-123", document_id="doc-xyz", size=1024)

  # Verify completion
  job = await job_store.get_job("job-123")
  assert job.status == JobStatus.DONE
  assert job.document_id == "doc-xyz"
"""

from abc import ABC, abstractmethod

from .models import JobInfo


class JobStorePort(ABC):
    """Abstract port for async job state management.

    Implementations handle persistence and retrieval of job metadata,
    status transitions, and result references for long-running operations.

    Implementations should be thread-safe or async-safe as appropriate
    for the deployment environment.
    """

    @abstractmethod
    async def create_job(self, job_id: str) -> JobInfo:
        """Create a new pending job.

        Args:
            job_id: Unique identifier for the job

        Returns:
            JobInfo with status=PENDING

        Raises:
            Exception: if job_id already exists
        """

    @abstractmethod
    async def get_job(self, job_id: str) -> JobInfo | None:
        """Retrieve job by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobInfo if found, None otherwise

        Note:
            May return None even if job was created, if it has expired
            and been cleaned up by the implementation.
        """

    @abstractmethod
    async def mark_running(self, job_id: str) -> JobInfo:
        """Transition job from PENDING to RUNNING.

        Args:
            job_id: Job identifier

        Returns:
            Updated JobInfo with status=RUNNING

        Raises:
            JobNotFoundError: if job doesn't exist
            JobAlreadyCompletedError: if job is in terminal state
        """

    @abstractmethod
    async def complete(self, job_id: str, document_id: str, size: int) -> JobInfo:
        """Transition job from RUNNING to DONE with result reference.

        Args:
            job_id: Job identifier
            document_id: External ID of persisted result (e.g., storage path)
            size: Size of result in bytes

        Returns:
            Updated JobInfo with status=DONE, document_id, and size

        Raises:
            JobNotFoundError: if job doesn't exist
            JobAlreadyCompletedError: if job is already DONE or FAILED
        """

    @abstractmethod
    async def fail(self, job_id: str, error: str) -> JobInfo:
        """Transition job from RUNNING to FAILED with error message.

        Args:
            job_id: Job identifier
            error: Error message describing the failure

        Returns:
            Updated JobInfo with status=FAILED and error message

        Raises:
            JobNotFoundError: if job doesn't exist
            JobAlreadyCompletedError: if job is already DONE or FAILED
        """

    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job (for cleanup or administrative operations).

        Args:
            job_id: Job identifier

        Returns:
            True if job was deleted, False if not found

        Note:
            Implementations may refuse to delete non-terminal jobs.
        """
