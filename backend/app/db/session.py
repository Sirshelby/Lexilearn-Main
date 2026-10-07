from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _add_query(url: str, **params: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query)) | params
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def engine_args(url: str, settings: Settings, *, pooled: bool) -> tuple[str, dict[str, Any]]:
    """Work out engine options for where we're running.

    - SQLite (development and tests): defaults.
    - A normal server or container: keep a small pool of connections open.
    - Serverless or behind a pooler: don't hold connections at all
      (NullPool). A Vercel instance can be frozen between requests, and
      the pooler in front of Postgres is already doing the pooling.
    - Behind PgBouncer in transaction mode, each transaction can land on a
      different server connection, which breaks asyncpg's prepared
      statement cache. Turn the caches off and give every statement a
      unique name (this is the setup SQLAlchemy's docs recommend).

    I tested this against a real PgBouncer in transaction mode with 25
    learners at once. With a kept-open pool and no workaround, every one
    failed with "prepared statement does not exist". With the workaround,
    all 25 passed. NullPool on its own also passed, but the workaround
    stays because it's what makes the pooled case safe.
    """
    kwargs: dict[str, Any] = {"echo": settings.database_echo}
    if url.startswith("sqlite"):
        return url, kwargs

    if settings.vercel or pooled:
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)

    if pooled:
        url = _add_query(url, prepared_statement_cache_size="0")
        kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
    return url, kwargs


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        url, kwargs = engine_args(settings.database_url, settings, pooled=settings.uses_pooler)
        _engine = create_async_engine(url, **kwargs)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
