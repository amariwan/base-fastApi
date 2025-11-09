from __future__ import annotations

import importlib
import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import create_engine, pool

from config import get_db_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _obj_to_metadata(obj: Any):
    return getattr(obj, "metadata", obj)  # akzeptiert Base oder direkt metadata


def _load_target_metadata():
    # Comma separated, e.g. "db.models:Base,account_service.models:Base"
    spec = (
        os.getenv("ALEMBIC_TARGETS")
        or config.get_main_option("target_metadata", "")
        or "db.models:Base"
    )
    metas = []
    for item in (s.strip() for s in spec.split(",") if s.strip()):
        mod, attr = item.split(":")
        obj = getattr(importlib.import_module(mod), attr)
        metas.append(_obj_to_metadata(obj))
    return metas[0] if len(metas) == 1 else metas


target_metadata = _load_target_metadata()


def _sync_url() -> str:
    db = get_db_settings()
    url = getattr(db, "DATABASE_URL", None)
    if not url:
        host = db.DB_HOST or "127.0.0.1"
        url = f"postgresql+psycopg://{db.DB_USERNAME}:{db.DB_PASSWORD}@{host}:{db.DB_PORT}/{db.DB_DATABASE}"
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table=config.get_main_option("version_table", "alembic_version"),
        version_table_schema=config.get_main_option("version_table_schema", None),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_sync_url(), poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            include_object=lambda obj, name, type_, reflected, compare_to: name
            != "alembic_version",
            version_table=config.get_main_option("version_table", "alembic_version"),
            version_table_schema=config.get_main_option("version_table_schema", None),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
