"""HTTP request/response schemas for Task 1 chat APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank.")
        return cleaned


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    route: Literal["llm"] | None = None
    status: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    route: Literal["llm"] = "llm"
    status: str = "Generating response"
