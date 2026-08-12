"""Conversation message routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service
from app.core.security import require_user_id
from app.models.schemas import MessageCreateRequest, MessageResponse, SendMessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: str,
    user_id: str = Depends(require_user_id),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageResponse]:
    return service.list_messages(owner_user_id=user_id, conversation_id=conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
)
async def send_message(
    conversation_id: str,
    body: MessageCreateRequest,
    user_id: str = Depends(require_user_id),
    service: ChatService = Depends(get_chat_service),
) -> SendMessageResponse:
    return await service.send_message(
        owner_user_id=user_id,
        conversation_id=conversation_id,
        content=body.content,
        mode=body.mode,
    )
