"""Password hashing and JWT helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()  # argon2id with the library's recommended defaults
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, get_settings().secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return _encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        }
    )


def create_refresh_token(user_id: uuid.UUID, token_id: uuid.UUID, expires_at: datetime) -> str:
    return _encode(
        {
            "sub": str(user_id),
            "jti": str(token_id),
            "type": "refresh",
            "iat": datetime.now(UTC),
            "exp": expires_at,
        }
    )


class TokenError(Exception):
    pass


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, get_settings().secret_key.get_secret_value(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError("wrong token type")
    return payload
