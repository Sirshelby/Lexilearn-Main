import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import LLM, DbSession, FallbackLLM, OwnedLearner, limit_per_user
from app.core.config import get_settings
from app.models import Conversation
from app.schemas.tutor import (
    ConversationDetail,
    ConversationOut,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.tutor import send_message

router = APIRouter(prefix="/learners/{learner_id}/tutor", tags=["tutor"])


async def _get_conversation(
    db: DbSession, learner_id: uuid.UUID, conversation_id: uuid.UUID, with_messages: bool = False
) -> Conversation:
    query = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.learner_id == learner_id
    )
    if with_messages:
        query = query.options(selectinload(Conversation.messages))
    conversation = await db.scalar(query)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(learner: OwnedLearner, db: DbSession) -> list[Conversation]:
    rows = await db.scalars(
        select(Conversation)
        .where(Conversation.learner_id == learner.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return list(rows)


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(learner: OwnedLearner, db: DbSession) -> Conversation:
    conversation = Conversation(learner_id=learner.id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: uuid.UUID, learner: OwnedLearner, db: DbSession) -> Conversation:
    return await _get_conversation(db, learner.id, conversation_id, with_messages=True)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: uuid.UUID, learner: OwnedLearner, db: DbSession) -> Response:
    conversation = await _get_conversation(db, learner.id, conversation_id)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    dependencies=[Depends(limit_per_user("tutor", lambda: get_settings().tutor_messages_per_minute))],
)
async def post_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    learner: OwnedLearner,
    db: DbSession,
    llm: LLM,
    fallback: FallbackLLM,
) -> SendMessageResponse:
    conversation = await _get_conversation(db, learner.id, conversation_id)
    user_message, reply = await send_message(db, learner, conversation, body.content, llm, fallback)
    return SendMessageResponse(
        user_message=MessageOut.model_validate(user_message),
        reply=MessageOut.model_validate(reply),
    )
