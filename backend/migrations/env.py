import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (registers every table)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine_args

target_metadata = Base.metadata


def _url_and_args():
    settings = get_settings()
    url = settings.migration_database_url
    # Only the pooled URL needs the PgBouncer workarounds.
    pooled = settings.uses_pooler and settings.database_url_unpooled is None
    url, kwargs = engine_args(url, settings, pooled=pooled)
    kwargs["poolclass"] = NullPool  # a one-off command, no point keeping a pool
    kwargs.pop("pool_size", None)
    kwargs.pop("max_overflow", None)
    return url, kwargs


def run_migrations_offline() -> None:
    context.configure(
        url=_url_and_args()[0],
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    # render_as_batch lets ALTER TABLE work on SQLite in development
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url, kwargs = _url_and_args()
    engine = create_async_engine(url, **kwargs)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
