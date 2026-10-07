from datetime import datetime

from pydantic import BaseModel

from app.schemas.literacy import SkillOut


class SkillStatusOut(BaseModel):
    code: str
    level: int
    title: str
    status: str  # locked | available | in_progress | mastered
    sessions: int
    accuracy: float | None


class RecentSessionOut(BaseModel):
    skill_code: str
    skill_title: str
    accuracy: float
    completed_at: datetime


class ProgressSummary(BaseModel):
    current_skill: SkillOut | None
    current_level: int
    level_title: str
    skills_mastered: int
    total_skills: int
    streak_days: int
    minutes_this_week: int
    sessions_this_week: int
    recent: list[RecentSessionOut]
    recommendations: list[str]
    skills: list[SkillStatusOut]
