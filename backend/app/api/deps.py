from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import get_rate_limiter
from app.core.security import TokenError, decode_token
from app.db.session import get_session
from app.llm import LLMProvider, get_fallback_llm, get_llm
from app.models import Learner, User

DbSession = Annotated[AsyncSession, Depends(get_session)]
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORISED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not signed in",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise _UNAUTHORISED
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, KeyError, ValueError):
        raise _UNAUTHORISED from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORISED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_owned_learner(learner_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Learner:
    """Load a learner profile, but only if it belongs to the signed-in account.

    Returns 404 rather than 403 for other people's learners so the API
    doesn't confirm that an id exists.
    """
    learner = await db.scalar(select(Learner).where(Learner.id == learner_id, Learner.owner_id == user.id))
    if learner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Learner not found")
    return learner


OwnedLearner = Annotated[Learner, Depends(get_owned_learner)]


def llm_provider() -> LLMProvider:
    return get_llm()


def fallback_provider() -> LLMProvider:
    return get_fallback_llm()


LLM = Annotated[LLMProvider, Depends(llm_provider)]
FallbackLLM = Annotated[LLMProvider, Depends(fallback_provider)]


def limit_per_user(bucket: str, limit: Callable[[], int]) -> Callable:
    async def dependency(user: CurrentUser) -> None:
        if not await get_rate_limiter().allow(f"{bucket}:{user.id}", limit()):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Slow down a little and try again soon")

    return dependency


def client_ip(request: Request) -> str:
    # Behind nginx or Vercel the real address arrives in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
