from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, limit_per_user
from app.core.config import get_settings
from app.services.speech import SpeechUnavailable, synthesize

router = APIRouter(prefix="/speech", tags=["speech"])


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    slow: bool = False


@router.post(
    "/tts",
    responses={200: {"content": {"audio/mpeg": {}}}, 503: {"description": "Use browser speech instead"}},
    dependencies=[Depends(limit_per_user("tts", lambda: get_settings().tts_requests_per_minute))],
)
async def tts(body: TTSRequest, _: CurrentUser, db: DbSession) -> Response:
    try:
        audio = await synthesize(db, body.text.strip(), slow=body.slow)
    except SpeechUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Speech service unavailable") from None
    return Response(
        content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"}
    )
