"""HTTP request/response schemas for chat and document APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DocumentStatus = Literal[
    "uploaded",
    "queued",
    "extracting",
    "chunking",
    "embedding",
    "indexing",
    "ready",
    "failed",
]

RouteName = Literal["llm", "rag"]


class ProjectCreateRequest(BaseModel):
    name: str = Field(default="My Research Project", min_length=1, max_length=200)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_user_id: str
    created_at: datetime


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    created_at: datetime


class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)
    # "llm" keeps general chat; "rag"/"auto" use documents when ready.
    mode: Literal["auto", "llm", "rag"] = "auto"

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank.")
        return cleaned


class CitationResponse(BaseModel):
    document_id: str
    chunk_id: str
    filename: str
    page_start: int | None = None
    page_end: int | None = None
    label: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    route: RouteName | None = None
    status: str | None = None
    provider: str | None = None
    model: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    created_at: datetime


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    route: RouteName = "llm"
    status: str = "Generating response"
    citations: list[CitationResponse] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int
    page_count: int | None = None
    status: DocumentStatus
    failure_code: str | None = None
    failure_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
