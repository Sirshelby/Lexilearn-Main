"""Mastery tracking and the progress summary shown on the dashboard.

Mastery rule (from OG practice, where a skill is only "done" once it's
consistent, not after one good day): at least MASTERY_SESSIONS completed
sessions, and the average of the last MASTERY_SESSIONS is MASTERY_ACCURACY or
higher. The numbers are constants here so they're easy to tune after testing
with real learners.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.literacy.curriculum import LEVEL_TITLES, SKILLS, SKILLS_BY_CODE, Skill, skill_index
from app.models import Learner, PracticeSession, SkillProgress
from app.schemas.literacy import SkillOut
from app.schemas.progress import ProgressSummary, RecentSessionOut, SkillStatusOut

MASTERY_SESSIONS = 3
MASTERY_ACCURACY = 0.85
STRUGGLE_ACCURACY = 0.6
RECENT_WINDOW = 5
MAX_MINUTES_PER_SESSION = 20  # don't count a tab left open overnight


def skill_out(skill: Skill) -> SkillOut:
    return SkillOut(
        code=skill.code,
        level=skill.level,
        title=skill.title,
        focus=skill.focus,
        tip=skill.tip,
        words=list(skill.words),
    )


async def load_progress(db: AsyncSession, learner_id: uuid.UUID) -> dict[str, SkillProgress]:
    rows = await db.scalars(select(SkillProgress).where(SkillProgress.learner_id == learner_id))
    return {row.skill_code: row for row in rows}


def current_skill(progress: dict[str, SkillProgress]) -> Skill | None:
    """The first skill in the sequence that isn't mastered yet."""
    for skill in SKILLS:
        row = progress.get(skill.code)
        if row is None or row.status != "mastered":
            return skill
    return None


def can_practise(skill: Skill, progress: dict[str, SkillProgress]) -> bool:
    """Learners can work on their current skill or review anything before it."""
    current = current_skill(progress)
    return current is None or skill_index(skill.code) <= skill_index(current.code)


def is_struggling(row: SkillProgress | None) -> bool:
    if row is None or len(row.recent_accuracy) < MASTERY_SESSIONS:
        return False
    return all(a < STRUGGLE_ACCURACY for a in row.recent_accuracy[-MASTERY_SESSIONS:])


def skill_statuses(progress: dict[str, SkillProgress]) -> list[SkillStatusOut]:
    current = current_skill(progress)
    current_idx = skill_index(current.code) if current else len(SKILLS)
    statuses = []
    for i, skill in enumerate(SKILLS):
        row = progress.get(skill.code)
        if row and row.status == "mastered":
            status = "mastered"
        elif i == current_idx:
            status = "in_progress" if row else "available"
        elif i < current_idx:
            status = "in_progress"
        else:
            status = "locked"
        accuracy = round(mean(row.recent_accuracy) * 100, 1) if row and row.recent_accuracy else None
        statuses.append(
            SkillStatusOut(
                code=skill.code,
                level=skill.level,
                title=skill.title,
                status=status,
                sessions=row.sessions_completed if row else 0,
                accuracy=accuracy,
            )
        )
    return statuses


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    row: SkillProgress
    mastered_now: bool


async def record_session(
    db: AsyncSession, learner_id: uuid.UUID, skill_code: str, correct: int, total: int
) -> SessionOutcome:
    row = await db.scalar(
        select(SkillProgress).where(
            SkillProgress.learner_id == learner_id, SkillProgress.skill_code == skill_code
        )
    )
    if row is None:
        row = SkillProgress(
            learner_id=learner_id,
            skill_code=skill_code,
            status="in_progress",
            sessions_completed=0,
            items_attempted=0,
            items_correct=0,
            recent_accuracy=[],
        )
        db.add(row)

    accuracy = correct / total if total else 0.0
    row.sessions_completed += 1
    row.items_attempted += total
    row.items_correct += correct
    # Reassign rather than mutate: SQLAlchemy doesn't track in-place JSON edits.
    row.recent_accuracy = [*row.recent_accuracy, round(accuracy, 3)][-RECENT_WINDOW:]

    mastered_now = False
    recent = row.recent_accuracy[-MASTERY_SESSIONS:]
    if (
        row.status != "mastered"
        and row.sessions_completed >= MASTERY_SESSIONS
        and mean(recent) >= MASTERY_ACCURACY
    ):
        row.status = "mastered"
        row.mastered_at = utcnow()
        mastered_now = True

    await db.flush()
    return SessionOutcome(row, mastered_now)


def _local_date(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def calculate_streak(practice_days: set[date], today: date) -> int:
    """Consecutive days with practice, ending today or yesterday.

    Counting from yesterday means the streak doesn't look broken first thing
    in the morning before the learner has practised.
    """
    day = today if today in practice_days else today - timedelta(days=1)
    streak = 0
    while day in practice_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _recommendations(
    current: Skill | None,
    progress: dict[str, SkillProgress],
    practised_today: bool,
) -> list[str]:
    recs: list[str] = []
    if current is None:
        return ["Every skill is mastered. Keep reading for fun in the reading room."]

    row = progress.get(current.code)
    if is_struggling(row):
        idx = skill_index(current.code)
        if idx > 0:
            prev = SKILLS[idx - 1]
            recs.append(f"{current.title} has been tricky. A quick review of {prev.title} can help.")
        recs.append("Ask Lexi to go through a word from this skill step by step.")
    elif row is None:
        recs.append(f"Start your next skill: {current.title}.")
    else:
        left = max(0, MASTERY_SESSIONS - row.sessions_completed)
        if left:
            recs.append(f"{left} more practice session{'s' if left != 1 else ''} to finish {current.title}.")
        else:
            recs.append(f"Keep practising {current.title} until it feels easy.")

    if not practised_today:
        recs.append("Five minutes of practice today keeps your streak going.")
    return recs


async def build_summary(db: AsyncSession, learner: Learner) -> ProgressSummary:
    progress = await load_progress(db, learner.id)
    current = current_skill(progress)
    tz = ZoneInfo(learner.timezone)
    now = datetime.now(UTC)
    today = _local_date(now, tz)

    # A year of history is plenty for the streak calculation.
    sessions = list(
        await db.scalars(
            select(PracticeSession)
            .where(
                PracticeSession.learner_id == learner.id,
                PracticeSession.completed_at.is_not(None),
                PracticeSession.completed_at >= now - timedelta(days=366),
            )
            .order_by(PracticeSession.completed_at.desc())
        )
    )

    days = {_local_date(s.completed_at, tz) for s in sessions if s.completed_at}
    week_ago = now - timedelta(days=7)
    this_week = [s for s in sessions if s.completed_at and s.completed_at >= week_ago]
    minutes = sum(
        min((s.completed_at - s.started_at).total_seconds() / 60, MAX_MINUTES_PER_SESSION)
        for s in this_week
        if s.completed_at
    )

    recent = [
        RecentSessionOut(
            skill_code=s.skill_code,
            skill_title=SKILLS_BY_CODE[s.skill_code].title
            if s.skill_code in SKILLS_BY_CODE
            else s.skill_code,
            accuracy=round((s.accuracy or 0) * 100, 1),
            completed_at=s.completed_at,
        )
        for s in sessions[:5]
        if s.completed_at
    ]

    level = current.level if current else max(LEVEL_TITLES)
    return ProgressSummary(
        current_skill=skill_out(current) if current else None,
        current_level=level,
        level_title=LEVEL_TITLES[level],
        skills_mastered=sum(1 for r in progress.values() if r.status == "mastered"),
        total_skills=len(SKILLS),
        streak_days=calculate_streak(days, today),
        minutes_this_week=round(minutes),
        sessions_this_week=len(this_week),
        recent=recent,
        recommendations=_recommendations(current, progress, today in days),
        skills=skill_statuses(progress),
    )
