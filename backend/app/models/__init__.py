"""Importing this package registers every table on Base.metadata (Alembic needs that)."""

from app.models.learner import Learner
from app.models.progress import PracticeSession, SkillProgress
from app.models.speech import TTSClip
from app.models.tutor import Conversation, Message
from app.models.user import RefreshToken, User

__all__ = [
    "Conversation",
    "Learner",
    "Message",
    "PracticeSession",
    "RefreshToken",
    "SkillProgress",
    "TTSClip",
    "User",
]
