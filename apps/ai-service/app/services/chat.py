"""Chat message use cases."""

from __future__ import annotations

from uuid import uuid4

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.models.schemas import MessageResponse, SendMessageResponse
from app.providers.llm import ChatMessage, LLMProvider, LLMRequest
from app.repositories.memory_store import MemoryStore, MessageRecord, utc_now

SYSTEM_INSTRUCTION = (
    "You are Academic Research Copilot, a helpful assistant for students and researchers. "
    "Be clear, concise, and accurate. Do not invent citations or claim access to private "
    "documents unless they are provided in the conversation."
)


class ChatService:
    def __init__(
        self,
        store: MemoryStore,
        llm: LLMProvider,
        settings: Settings,
    ) -> None:
        self._store = store
        self._llm = llm
        self._settings = settings

    def list_messages(self, *, owner_user_id: str, conversation_id: str) -> list[MessageResponse]:
        conversation = self._store.get_conversation(
            conversation_id=conversation_id,
            owner_user_id=owner_user_id,
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        records = self._store.list_messages(conversation_id=conversation_id)
        return [_to_message_response(message) for message in records]

    async def send_message(
        self,
        *,
        owner_user_id: str,
        conversation_id: str,
        content: str,
    ) -> SendMessageResponse:
        conversation = self._store.get_conversation(
            conversation_id=conversation_id,
            owner_user_id=owner_user_id,
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")

        cleaned = content.strip()
        if not cleaned:
            raise ValidationAppError("Message content cannot be blank.")
        max_chars = self._settings.max_message_chars
        if len(cleaned) > max_chars:
            raise ValidationAppError(
                f"Message exceeds the maximum length of {max_chars} characters."
            )

        user_record = MessageRecord(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=cleaned,
            created_at=utc_now(),
        )
        self._store.append_message(user_record)

        history = self._store.list_messages(conversation_id=conversation_id)
        # Include prior turns + the just-saved user message; cap history window.
        capped = history[-self._settings.max_history_messages :]
        llm_messages = [
            ChatMessage(role="user" if m.role == "user" else "assistant", content=m.content)
            for m in capped
            if m.role in {"user", "assistant"}
        ]

        llm_response = await self._llm.generate(
            LLMRequest(
                messages=llm_messages,
                model=self._settings.llm_model,
                system_instruction=SYSTEM_INSTRUCTION,
            )
        )

        assistant_record = MessageRecord(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=llm_response.text,
            created_at=utc_now(),
            route="llm",
            status=None,
            provider=llm_response.provider,
            model=llm_response.model,
        )
        self._store.append_message(assistant_record)

        return SendMessageResponse(
            user_message=_to_message_response(user_record),
            assistant_message=_to_message_response(assistant_record),
            route="llm",
            status="Generating response",
        )


def _to_message_response(message: MessageRecord) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,  # type: ignore[arg-type]
        content=message.content,
        route=message.route,  # type: ignore[arg-type]
        status=message.status,
        provider=message.provider,
        model=message.model,
        created_at=message.created_at,
    )
