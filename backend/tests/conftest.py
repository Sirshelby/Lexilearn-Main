import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("ELEVENLABS_API_KEY", None)

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models
from app.api.deps import fallback_provider, llm_provider
from app.core.rate_limit import get_rate_limiter, memory_limiter
from app.db.base import Base
from app.db.session import get_session
from app.llm.offline import OfflineProvider
from app.main import create_app

PASSWORD = "correct-horse-battery"


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def app(session_factory):
    application = create_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_session] = _session
    application.dependency_overrides[llm_provider] = lambda: OfflineProvider(seed=1)
    application.dependency_overrides[fallback_provider] = lambda: OfflineProvider(seed=1)
    get_rate_limiter.cache_clear()
    memory_limiter.reset()
    return application


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register(client: httpx.AsyncClient, email: str = "parent@example.com", **extra) -> dict:
    body = {
        "email": email,
        "password": PASSWORD,
        "display_name": "Ada Parent",
        "learner_name": "Sam",
        **extra,
    }
    response = await client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(data: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
async def account(client) -> dict:
    data = await register(client)
    return {"headers": auth_header(data), "learner_id": data["user"]["learners"][0]["id"], "data": data}
