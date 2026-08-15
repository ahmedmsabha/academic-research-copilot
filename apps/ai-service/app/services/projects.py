"""Project and conversation use cases."""

from __future__ import annotations

from app.core.errors import NotFoundError
from app.models.schemas import (
    ConversationResponse,
    ProjectResponse,
)
from app.repositories.memory_store import MemoryStore


class ProjectService:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def create_project(self, *, owner_user_id: str, name: str) -> ProjectResponse:
        project = self._store.create_project(owner_user_id=owner_user_id, name=name)
        return ProjectResponse(
            id=project.id,
            name=project.name,
            owner_user_id=project.owner_user_id,
            created_at=project.created_at,
        )

    def list_projects(self, *, owner_user_id: str) -> list[ProjectResponse]:
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                owner_user_id=p.owner_user_id,
                created_at=p.created_at,
            )
            for p in self._store.list_projects(owner_user_id=owner_user_id)
        ]

    def ensure_default_project(self, *, owner_user_id: str) -> ProjectResponse:
        existing = self._store.list_projects(owner_user_id=owner_user_id)
        if existing:
            project = existing[0]
            return ProjectResponse(
                id=project.id,
                name=project.name,
                owner_user_id=project.owner_user_id,
                created_at=project.created_at,
            )
        return self.create_project(owner_user_id=owner_user_id, name="My Research Project")

    def create_conversation(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        title: str,
    ) -> ConversationResponse:
        project = self._store.get_project(project_id=project_id, owner_user_id=owner_user_id)
        if project is None:
            raise NotFoundError("Project not found.")
        conversation = self._store.create_conversation(
            project_id=project_id,
            owner_user_id=owner_user_id,
            title=title,
        )
        return ConversationResponse(
            id=conversation.id,
            project_id=conversation.project_id,
            title=conversation.title,
            created_at=conversation.created_at,
        )

    def list_conversations(
        self,
        *,
        owner_user_id: str,
        project_id: str,
    ) -> list[ConversationResponse]:
        project = self._store.get_project(project_id=project_id, owner_user_id=owner_user_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return [
            ConversationResponse(
                id=conversation.id,
                project_id=conversation.project_id,
                title=conversation.title,
                created_at=conversation.created_at,
            )
            for conversation in self._store.list_conversations(
                project_id=project_id,
                owner_user_id=owner_user_id,
            )
        ]
