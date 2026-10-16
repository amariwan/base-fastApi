"""Exceptions for async job operations."""


class JobError(Exception):
    """Base exception for job store operations."""

    pass


class JobNotFoundError(JobError):
    """Raised when a job ID does not exist or has expired.

    HTTP: 404 Not Found
    """

    def __init__(self, job_id: str, message: str | None = None):
        self.job_id = job_id
        self.message = message or f"Job {job_id} not found"
        super().__init__(self.message)


class JobExpiredError(JobError):
    """Raised when attempting to access an expired job.

    HTTP: 410 Gone
    """

    def __init__(self, job_id: str, message: str | None = None):
        self.job_id = job_id
        self.message = message or f"Job {job_id} has expired"
        super().__init__(self.message)


class JobAlreadyCompletedError(JobError):
    """Raised when attempting to modify a job that is already in terminal state.

    HTTP: 409 Conflict
    """

    def __init__(self, job_id: str, status: str, message: str | None = None):
        self.job_id = job_id
        self.status = status
        self.message = message or f"Job {job_id} is already {status}"
        super().__init__(self.message)
