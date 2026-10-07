from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, OwnedLearner
from app.models import Learner
from app.schemas.learner import LearnerCreate, LearnerOut, LearnerUpdate

router = APIRouter(prefix="/learners", tags=["learners"])

MAX_LEARNERS_PER_ACCOUNT = 30  # a teacher with a class; raise once we add proper school accounts


@router.get("", response_model=list[LearnerOut])
async def list_learners(user: CurrentUser, db: DbSession) -> list[Learner]:
    rows = await db.scalars(select(Learner).where(Learner.owner_id == user.id).order_by(Learner.created_at))
    return list(rows)


@router.post("", response_model=LearnerOut, status_code=status.HTTP_201_CREATED)
async def create_learner(body: LearnerCreate, user: CurrentUser, db: DbSession) -> Learner:
    count = await db.scalar(select(func.count()).select_from(Learner).where(Learner.owner_id == user.id))
    if (count or 0) >= MAX_LEARNERS_PER_ACCOUNT:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account has reached its learner limit")
    learner = Learner(
        owner_id=user.id,
        name=body.name.strip(),
        age_band=body.age_band,
        timezone=body.timezone,
        preferences={},
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return learner


@router.get("/{learner_id}", response_model=LearnerOut)
async def get_learner(learner: OwnedLearner) -> Learner:
    return learner


@router.patch("/{learner_id}", response_model=LearnerOut)
async def update_learner(body: LearnerUpdate, learner: OwnedLearner, db: DbSession) -> Learner:
    changes = body.model_dump(exclude_unset=True, exclude={"preferences"})
    for field, value in changes.items():
        if value is not None:
            setattr(learner, field, value.strip() if isinstance(value, str) else value)
    if body.preferences is not None:
        learner.preferences = body.preferences.model_dump()
    await db.commit()
    await db.refresh(learner)
    return learner


@router.delete("/{learner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learner(learner: OwnedLearner, user: CurrentUser, db: DbSession) -> Response:
    count = await db.scalar(select(func.count()).select_from(Learner).where(Learner.owner_id == user.id))
    if (count or 0) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account needs at least one learner")
    await db.delete(learner)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
