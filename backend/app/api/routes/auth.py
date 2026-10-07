from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.core.rate_limit import get_rate_limiter
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Learner, RefreshToken, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "lexilearn_refresh"


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        expires=expires_at,
        path=f"{settings.api_prefix}/auth",
    )


async def _issue_tokens(db: DbSession, user: User, response: Response) -> TokenResponse:
    settings = get_settings()
    token_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    db.add(RefreshToken(id=token_id, user_id=user.id, expires_at=expires_at))
    _set_refresh_cookie(response, create_refresh_token(user.id, token_id, expires_at), expires_at)
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_minutes * 60,
    )


async def _load_user(db: DbSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(select(User).options(selectinload(User.learners)).where(User.id == user_id))
    assert user is not None
    return user


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: DbSession) -> AuthResponse:
    email = body.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        account_type=body.account_type,
    )
    db.add(user)
    await db.flush()

    first_name = body.learner_name or body.display_name.split()[0]
    db.add(
        Learner(
            owner_id=user.id,
            name=first_name.strip(),
            age_band=body.learner_age_band,
            timezone=body.timezone,
            preferences={},
        )
    )

    tokens = await _issue_tokens(db, user, response)
    await db.commit()
    loaded = await _load_user(db, user.id)
    return AuthResponse(**tokens.model_dump(), user=UserOut.model_validate(loaded))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    email = body.email.lower()
    key = f"login:{client_ip(request)}:{email}"
    if not await get_rate_limiter().allow(key, get_settings().login_attempts_per_minute):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Wait a minute and try again."
        )

    user = await db.scalar(select(User).where(User.email == email))
    # Same message for "no such email" and "wrong password" on purpose.
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")

    tokens = await _issue_tokens(db, user, response)
    await db.commit()
    loaded = await _load_user(db, user.id)
    return AuthResponse(**tokens.model_dump(), user=UserOut.model_validate(loaded))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: DbSession) -> TokenResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        payload = decode_token(raw, "refresh")
        token_id = uuid.UUID(payload["jti"])
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in") from None

    stored = await db.get(RefreshToken, token_id)
    now = datetime.now(UTC)
    if stored is None or stored.user_id != user_id or stored.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    if stored.revoked_at is not None:
        # A revoked token being used again means it was probably stolen.
        # Sign out every session for this user to be safe.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    stored.revoked_at = now  # rotate: each refresh token works once
    tokens = await _issue_tokens(db, user, response)
    await db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbSession) -> Response:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        try:
            payload = decode_token(raw, "refresh")
            stored = await db.get(RefreshToken, uuid.UUID(payload["jti"]))
            if stored and stored.revoked_at is None:
                stored.revoked_at = datetime.now(UTC)
                await db.commit()
        except (TokenError, KeyError, ValueError):
            pass
    response.delete_cookie(REFRESH_COOKIE, path=f"{get_settings().api_prefix}/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser, db: DbSession) -> UserOut:
    return UserOut.model_validate(await _load_user(db, user.id))
