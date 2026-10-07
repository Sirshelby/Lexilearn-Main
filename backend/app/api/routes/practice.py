import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnedLearner
from app.db.base import utcnow
from app.literacy.curriculum import SKILLS_BY_CODE
from app.models import PracticeSession
from app.schemas.practice import (
    AnswerRequest,
    AnswerResult,
    CompleteResult,
    PracticeSessionOut,
    StartPracticeRequest,
)
from app.services import practice as practice_service
from app.services.progress import can_practise, current_skill, load_progress, record_session

router = APIRouter(prefix="/learners/{learner_id}/practice", tags=["practice"])


async def _get_session(db: DbSession, learner_id: uuid.UUID, session_id: uuid.UUID) -> PracticeSession:
    session = await db.scalar(
        select(PracticeSession).where(
            PracticeSession.id == session_id, PracticeSession.learner_id == learner_id
        )
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Practice session not found")
    return session


@router.post("/sessions", response_model=PracticeSessionOut, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: StartPracticeRequest, learner: OwnedLearner, db: DbSession
) -> PracticeSessionOut:
    progress = await load_progress(db, learner.id)

    if body.skill_code:
        skill = SKILLS_BY_CODE.get(body.skill_code)
        if skill is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown skill")
        if not can_practise(skill, progress):
            raise HTTPException(status.HTTP_409_CONFLICT, "Finish the earlier skills first")
    else:
        skill = current_skill(progress) or SKILLS_BY_CODE["8.5"]

    items = practice_service.build_items(skill)
    session = PracticeSession(learner_id=learner.id, skill_code=skill.code, items=items, answers=[])
    db.add(session)
    await db.commit()

    return PracticeSessionOut(
        id=session.id,
        skill_code=skill.code,
        skill_title=skill.title,
        tip=skill.tip,
        items=[practice_service.public_item(i, item) for i, item in enumerate(items)],
    )


@router.post("/sessions/{session_id}/answers", response_model=AnswerResult)
async def answer(
    session_id: uuid.UUID, body: AnswerRequest, learner: OwnedLearner, db: DbSession
) -> AnswerResult:
    session = await _get_session(db, learner.id, session_id)
    if session.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This session is already finished")
    if body.item_index >= len(session.items):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No such item")

    item = session.items[body.item_index]
    result = practice_service.grade(item, body.answer)

    # Only the first answer to each item counts towards the score.
    if not any(a["index"] == body.item_index for a in session.answers):
        session.answers = [
            *session.answers,
            {"index": body.item_index, "answer": body.answer, "correct": result.correct},
        ]
        await db.commit()
    return result


@router.post("/sessions/{session_id}/complete", response_model=CompleteResult)
async def complete(session_id: uuid.UUID, learner: OwnedLearner, db: DbSession) -> CompleteResult:
    session = await _get_session(db, learner.id, session_id)
    if session.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This session is already finished")

    total = len(session.items)
    correct = sum(1 for a in session.answers if a["correct"])
    session.accuracy = correct / total if total else 0.0
    session.completed_at = utcnow()

    outcome = await record_session(db, learner.id, session.skill_code, correct, total)
    await db.commit()

    progress = await load_progress(db, learner.id)
    nxt = current_skill(progress)
    return CompleteResult(
        skill_code=session.skill_code,
        correct=correct,
        total=total,
        accuracy=round(session.accuracy * 100, 1),
        mastered_now=outcome.mastered_now,
        skill_status=outcome.row.status,
        next_skill_code=nxt.code if nxt else None,
    )
