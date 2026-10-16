# Core Email

`core_email` separates message construction, direct delivery, and queueing.
The default console backend logs only subject and recipient count. Set
`EMAIL_BACKEND=smtp` for SMTP.

When `EMAIL_USE_CELERY=true`, `EmailDispatcher` enqueues the configured task.
If Celery is not installed or enqueueing fails, it delivers through the direct
backend instead. Install Celery with `uv sync --extra celery`.

Register the worker task on the application's Celery instance:

```python
from app.core.core_email import register_celery_email_task

register_celery_email_task(celery_app)
```

The default task name is `app.core.email.send`; override it with
`EMAIL_CELERY_TASK_NAME` on both producer and worker.
