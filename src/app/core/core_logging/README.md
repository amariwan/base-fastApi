# Core Logging

`core_logging` provides the application's stdlib-compatible logger adapters,
JSON formatter, and journey diagnostics. It is infrastructure, not a domain
logging framework.

## Lifecycle

`AppLogger.setup_logging()` is called explicitly by `app.views.create_app()`.
Importing `AppLogger`, `JourneyLogger`, or the formatter does not mutate the
process-wide logging configuration. This keeps imports safe for tests, CLI
tools, and worker modules and makes configuration ownership visible at the
application boundary.

## Public behavior

- `fastapi_logger` is the application logger used by the HTTP/runtime layer.
- `system_logger`, `single_logger`, and `journey_logger` add a stable
  `log_type` field through `LogTypeAdapter`.
- `JourneyTracker` records ordered, timestamped diagnostic steps and emits a
  structured journey event when requested.
- `MyJSONFormatter` preserves configured extra fields and emits a compact
  JSON record.

The existing mixed-case module names remain compatibility surfaces because
feature services import them directly. New modules should use normal Python
`snake_case` names; renaming the compatibility modules is a separate
migration and is not required for the lifecycle boundary.

## Rules

Do not configure logging from module import code, silently swallow logging
errors, or make feature code depend on a concrete handler/formatter. Keep
request context in `extra` or a dedicated adapter and preserve the standard
`logging.Logger` calling contract.
