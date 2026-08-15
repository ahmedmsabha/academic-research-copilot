"""HTTP request/response schemas for chat and document APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.prompts.library import PromptStrategy

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

RouteName = Literal["llm", "rag", "calculator", "web_search", "weather"]
RoutePreference = Literal["auto", "llm", "rag", "calculator", "web_search", "weather"]


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
    # "auto" lets the agent router choose; explicit modes pin a route.
    mode: RoutePreference = "auto"

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


class WebSourceResponse(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    provider: str
    retrieved_at: datetime | None = None


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
    web_sources: list[WebSourceResponse] = Field(default_factory=list)
    created_at: datetime


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    route: RouteName = "llm"
    status: str = "Generating response"
    citations: list[CitationResponse] = Field(default_factory=list)
    web_sources: list[WebSourceResponse] = Field(default_factory=list)


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


class PromptExperimentCreateRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=8000)
    strategies: list[PromptStrategy] | None = None

    @field_validator("input")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt Lab input cannot be blank.")
        return cleaned

    @field_validator("strategies")
    @classmethod
    def reject_empty_strategies(
        cls, value: list[PromptStrategy] | None
    ) -> list[PromptStrategy] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("Select at least one prompting strategy.")
        # Preserve order while dropping duplicates.
        seen: set[str] = set()
        unique: list[PromptStrategy] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique


class PromptExperimentRatingRequest(BaseModel):
    rating_accuracy: int | None = Field(default=None, ge=1, le=5)
    rating_clarity: int | None = Field(default=None, ge=1, le=5)
    rating_research_usefulness: int | None = Field(default=None, ge=1, le=5)


class PromptExperimentResponse(BaseModel):
    id: str | None = None
    run_id: str
    project_id: str
    strategy: PromptStrategy
    template_version: str
    input: str
    output: str
    model: str | None = None
    provider: str | None = None
    elapsed_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    rating_accuracy: int | None = None
    rating_clarity: int | None = None
    rating_research_usefulness: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class PromptExperimentRunResponse(BaseModel):
    run_id: str
    project_id: str
    input: str
    results: list[PromptExperimentResponse]


class PromptExperimentRunListResponse(BaseModel):
    runs: list[PromptExperimentRunResponse]


class PromptStrategyGuideResponse(BaseModel):
    id: PromptStrategy
    name: str
    description: str
    when_better: str
    user_template: str
    template_version: str


class PromptLibraryResponse(BaseModel):
    version: str
    strategies: list[PromptStrategyGuideResponse]
