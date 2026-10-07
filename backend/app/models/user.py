from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UTCDateTime, UUIDPrimaryKey, utcnow

if TYPE_CHECKING:
    from app.models.learner import Learner


class User(UUIDPrimaryKey, Timestamps, Base):
    """An account. Parents and teachers own one or more learner profiles;
    older learners can have an account of their own with a single profile."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    account_type: Mapped[str] = mapped_column(String(20), default="parent")  # parent | teacher | learner
    is_active: Mapped[bool] = mapped_column(default=True)

    learners: Mapped[list[Learner]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", order_by="Learner.created_at"
    )


class RefreshToken(Base):
    """One row per issued refresh token so we can revoke and rotate them."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # same as the token's jti
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
