from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UTCDateTime, UUIDPrimaryKey, utcnow


class SkillProgress(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "skill_progress"
    __table_args__ = (UniqueConstraint("learner_id", "skill_code"),)

    learner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"), index=True)
    skill_code: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="in_progress")  # in_progress | mastered
    sessions_completed: Mapped[int] = mapped_column(default=0)
    items_attempted: Mapped[int] = mapped_column(default=0)
    items_correct: Mapped[int] = mapped_column(default=0)
    # Accuracy of the last few sessions, newest last. Used for the mastery rule.
    recent_accuracy: Mapped[list[float]] = mapped_column(JSON, default=list)
    mastered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class PracticeSession(UUIDPrimaryKey, Base):
    """A single run of practice items for one skill.

    The correct answers live in `items` on the server and are never sent to
    the browser until the learner has answered, so grading can be trusted.
    """

    __tablename__ = "practice_sessions"
    __table_args__ = (Index("ix_practice_sessions_learner_completed", "learner_id", "completed_at"),)

    learner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learners.id", ondelete="CASCADE"))
    skill_code: Mapped[str] = mapped_column(String(8))
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    answers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    accuracy: Mapped[float | None] = mapped_column(default=None)
