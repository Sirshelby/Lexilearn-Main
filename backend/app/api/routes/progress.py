from fastapi import APIRouter

from app.api.deps import DbSession, OwnedLearner
from app.schemas.progress import ProgressSummary
from app.services.progress import build_summary

router = APIRouter(prefix="/learners/{learner_id}", tags=["progress"])


@router.get("/progress", response_model=ProgressSummary)
async def progress(learner: OwnedLearner, db: DbSession) -> ProgressSummary:
    return await build_summary(db, learner)
