from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.user import User


class Learner(UUIDPrimaryKey, Timestamps, Base):
    """The person actually doing the reading.

    We deliberately store very little about learners (a first name or
    nickname and an age band, no date of birth) because most of them are
    children. Reading preferences are a JSON blob validated by
    schemas.learner.ReadingPreferences, so adding a setting doesn't need a
    migration.
    """

    __tablename__ = "learners"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    age_band: Mapped[str | None] = mapped_column(String(10), default=None)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    owner: Mapped[User] = relationship(back_populates="learners")
