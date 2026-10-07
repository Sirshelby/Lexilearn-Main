from __future__ import annotations

from datetime import datetime

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class TTSClip(Base):
    """Cached speech audio, keyed by a hash of the text and voice settings.

    Phonics practice repeats the same short words constantly, so most audio
    is requested many times. Keeping it in Postgres means the cache works
    the same in Docker and on Vercel (which has no permanent disk), with no
    extra service to run. Clips are small: a single word is a few kilobytes.
    """

    __tablename__ = "tts_clips"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    audio: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
