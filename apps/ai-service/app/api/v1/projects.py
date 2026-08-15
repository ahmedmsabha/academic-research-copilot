"""Project and project-scoped conversation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_project_service
from app.core.security import require_user_id
from app.models.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    ProjectCreateRequest,
    ProjectResponse,
)
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    user_id: str = Depends(require_user_id),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return service.list_projects(owner_user_id=user_id)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreateRequest,
    user_id: str = Depends(require_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    # Task 1: if the caller already has projects, reuse the default workspace.
    # Explicit non-default names still create a new project.
    if body.name.strip() in {"", "My Research Project"}:
        return service.ensure_default_project(owner_user_id=user_id)
    return service.create_project(owner_user_id=user_id, name=body.name)


@router.get("/{project_id}/conversations", response_model=list[ConversationResponse])
def list_conversations(
    project_id: str,
    user_id: str = Depends(require_user_id),
    service: ProjectService = Depends(get_project_service),
) -> list[ConversationResponse]:
    return service.list_conversations(owner_user_id=user_id, project_id=project_id)


@router.post(
    "/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=201,
)
def create_conversation(
    project_id: str,
    body: ConversationCreateRequest,
    user_id: str = Depends(require_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ConversationResponse:
    return service.create_conversation(
        owner_user_id=user_id,
        project_id=project_id,
        title=body.title,
    )
