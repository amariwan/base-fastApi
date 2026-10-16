# Core Database

`core_db` owns SQLAlchemy metadata, database URL construction, async session
lifecycle, and Alembic startup helpers. The application lifespan decides when
startup work runs; importing database modules must not open a connection.

`startup_migrations.py` contains revision inspection and advisory-lock
coordination. `startup_checks.py` remains the application-level orchestrator
that combines database and storage probes with migration policy. The old
imports from `app.core.startup_checks` remain available as compatibility
aliases while callers migrate to the `core_db` boundary.

The stable package surface exposes `DatabaseSessionManager`,
`DBSessionDep`, `get_db_session`, and `get_sessionmanager`; callers should
not need to import the implementation module directly. Transaction commits
remain an explicit responsibility of the application/service layer. Session
cleanup and rollback on exceptions are owned by the session manager.
