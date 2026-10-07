"""Tests for the pieces that only matter in production: database URLs from
hosting providers, serverless engine settings, shared rate limiting, the
speech cache and the Vercel build step."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy.pool import NullPool

from app.core.config import Settings, normalize_database_url
from app.core.rate_limit import RedisRateLimiter
from app.db.session import engine_args
from app.services import speech

NEON_POOLED = (
    "postgres://lexi:secret@ep-quiet-sky-123456-pooler.eu-central-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)
NEON_DIRECT = "postgres://lexi:secret@ep-quiet-sky-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require"


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


# ---------- database URLs ----------


def test_provider_urls_are_rewritten_for_asyncpg() -> None:
    assert normalize_database_url(NEON_POOLED) == (
        "postgresql+asyncpg://lexi:secret@ep-quiet-sky-123456-pooler.eu-central-1.aws.neon.tech/neondb?ssl=require"
    )


@pytest.mark.parametrize(
    "url",
    ["sqlite+aiosqlite:///./lexilearn.db", "postgresql+asyncpg://u:p@localhost:5432/db"],
)
def test_urls_that_already_work_are_left_alone(url: str) -> None:
    assert normalize_database_url(url) == url


def test_pooler_is_detected_from_neon_host_names() -> None:
    assert settings(database_url=NEON_POOLED).uses_pooler
    assert not settings(database_url=NEON_DIRECT).uses_pooler
    assert settings(database_url="postgresql://u:p@localhost:6432/db", database_pooler=True).uses_pooler


def test_migrations_use_the_direct_connection_when_there_is_one() -> None:
    s = settings(database_url=NEON_POOLED, database_url_unpooled=NEON_DIRECT)
    assert "-pooler" not in s.migration_database_url
    assert s.migration_database_url.startswith("postgresql+asyncpg://")


def test_serverless_engine_behind_a_pooler() -> None:
    s = settings(database_url=NEON_POOLED, vercel=True)
    url, kwargs = engine_args(s.database_url, s, pooled=s.uses_pooler)
    assert kwargs["poolclass"] is NullPool
    assert "prepared_statement_cache_size=0" in url
    assert kwargs["connect_args"]["statement_cache_size"] == 0
    name = kwargs["connect_args"]["prepared_statement_name_func"]
    assert name() != name()  # every statement gets a unique name


def test_long_running_server_keeps_a_pool() -> None:
    s = settings(database_url="postgresql://u:p@db:5432/lexilearn")
    _, kwargs = engine_args(s.database_url, s, pooled=False)
    assert "poolclass" not in kwargs
    assert kwargs["pool_size"] == 10


def test_redis_settings_accept_the_names_vercel_injects(monkeypatch) -> None:
    monkeypatch.setenv("KV_REST_API_URL", "https://example.upstash.io")
    monkeypatch.setenv("KV_REST_API_TOKEN", "token")
    s = settings()
    assert s.redis_rest_url == "https://example.upstash.io"
    assert s.redis_rest_token is not None


# ---------- shared rate limiting ----------


def fake_redis() -> tuple[httpx.AsyncClient, dict[str, int]]:
    counts: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token"
        commands = json.loads(request.content)
        key = commands[0][1]
        counts[key] = counts.get(key, 0) + 1
        return httpx.Response(200, json=[{"result": counts[key]}, {"result": 1}])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), counts


async def test_redis_limiter_blocks_after_the_limit() -> None:
    client, _ = fake_redis()
    limiter = RedisRateLimiter("https://redis.example", "token", client=client)
    assert [await limiter.allow("login:a", 3) for _ in range(5)] == [True, True, True, False, False]
    assert await limiter.allow("login:b", 3)  # other keys are counted separately


async def test_redis_limiter_lets_requests_through_if_redis_is_down() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    limiter = RedisRateLimiter("https://redis.example", "token", client=client)
    assert await limiter.allow("tutor:x", 1)
    assert await limiter.allow("tutor:x", 1)


# ---------- speech cache ----------


async def test_speech_is_cached_in_the_database(session_factory, monkeypatch) -> None:
    monkeypatch.setattr(speech, "get_settings", lambda: settings(elevenlabs_api_key="key"))
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=b"ID3-fake-audio")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with session_factory() as db:
        first = await speech.synthesize(db, "cat", client=client)
        second = await speech.synthesize(db, "cat", client=client)
        assert first == second == b"ID3-fake-audio"
        assert len(calls) == 1
        assert calls[0].headers["xi-api-key"] == "key"

        await speech.synthesize(db, "cat", slow=True, client=client)  # slow is a different clip
        assert len(calls) == 2

        passage = "The cat sat on the mat. " * 10  # too long to be worth caching
        await speech.synthesize(db, passage, client=client)
        await speech.synthesize(db, passage, client=client)
        assert len(calls) == 4


async def test_speech_provider_errors_become_unavailable(session_factory, monkeypatch) -> None:
    monkeypatch.setattr(speech, "get_settings", lambda: settings(elevenlabs_api_key="revoked"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    async with session_factory() as db:
        with pytest.raises(speech.SpeechUnavailable):
            await speech.synthesize(db, "cat", client=client)


# ---------- Vercel build step ----------


def load_build_script():
    path = Path(__file__).parent.parent / "scripts" / "vercel_build.py"
    spec = importlib.util.spec_from_file_location("vercel_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_skips_migrations_for_previews(monkeypatch) -> None:
    build = load_build_script()
    ran = []
    monkeypatch.setattr(build.subprocess, "call", lambda cmd: ran.append(cmd) or 0)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("MIGRATE_PREVIEWS", raising=False)
    assert build.main() == 0
    assert ran == []


def test_build_migrates_production_and_fails_without_a_database(monkeypatch) -> None:
    build = load_build_script()
    ran = []
    monkeypatch.setattr(build.subprocess, "call", lambda cmd: ran.append(cmd) or 0)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_UNPOOLED", raising=False)
    assert build.main() == 1

    monkeypatch.setenv("DATABASE_URL_UNPOOLED", NEON_DIRECT)
    assert build.main() == 0
    assert ran[0][1:] == ["-m", "alembic", "upgrade", "head"]
