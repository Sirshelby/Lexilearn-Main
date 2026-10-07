from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: DbSession) -> dict:
    await db.execute(text("SELECT 1"))
    settings = get_settings()
    return {
        "status": "ok",
        "tutor": "online" if settings.llm_api_key else "offline",
        "speech": "premium" if settings.elevenlabs_api_key else "browser",
    }
