from fastapi import APIRouter, Depends

from app.api.deps import LLM, DbSession, OwnedLearner, limit_per_user
from app.core.config import get_settings
from app.literacy.curriculum import MAX_LEVEL
from app.schemas.reading import PassageOut, PassageRequest
from app.services.progress import current_skill, load_progress
from app.services.reading import get_passage

router = APIRouter(prefix="/learners/{learner_id}/reading", tags=["reading"])


@router.post(
    "/passage",
    response_model=PassageOut,
    dependencies=[Depends(limit_per_user("passage", lambda: get_settings().tutor_messages_per_minute))],
)
async def passage(body: PassageRequest, learner: OwnedLearner, db: DbSession, llm: LLM) -> PassageOut:
    progress = await load_progress(db, learner.id)
    skill = current_skill(progress)
    learner_level = skill.level if skill else MAX_LEVEL
    # Allow reading below your level, never above it.
    level = min(body.level or learner_level, learner_level)
    topic = body.topic.strip() if body.topic and body.topic.strip() else None
    return await get_passage(level, topic, llm)
