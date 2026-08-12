"""Postgres-backed store using Prisma-managed tables."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationRow, MessageRow, ProjectRow
from app.repositories.memory_store import (
    ConversationRecord,
    MessageRecord,
    ProjectRecord,
    utc_now,
)


class PostgresStore:
    """Duck-typed replacement for MemoryStore backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_project(self, *, owner_user_id: str, name: str) -> ProjectRecord:
        row = ProjectRow(
            id=str(uuid4()),
            name=name.strip() or "My Research Project",
            owner_user_id=owner_user_id,
            created_at=utc_now(),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _project(row)

    def list_projects(self, *, owner_user_id: str) -> list[ProjectRecord]:
        rows = self._session.scalars(
            select(ProjectRow)
            .where(ProjectRow.owner_user_id == owner_user_id)
            .order_by(ProjectRow.created_at.asc())
        ).all()
        return [_project(row) for row in rows]

    def get_project(self, *, project_id: str, owner_user_id: str) -> ProjectRecord | None:
        row = self._session.scalar(
            select(ProjectRow).where(
                ProjectRow.id == project_id,
                ProjectRow.owner_user_id == owner_user_id,
            )
        )
        return _project(row) if row else None

    def create_conversation(
        self,
        *,
        project_id: str,
        owner_user_id: str,
        title: str,
    ) -> ConversationRecord:
        row = ConversationRow(
            id=str(uuid4()),
            project_id=project_id,
            owner_user_id=owner_user_id,
            title=title.strip() or "New chat",
            created_at=utc_now(),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _conversation(row)

    def get_conversation(
        self,
        *,
        conversation_id: str,
        owner_user_id: str,
    ) -> ConversationRecord | None:
        row = self._session.scalar(
            select(ConversationRow).where(
                ConversationRow.id == conversation_id,
                ConversationRow.owner_user_id == owner_user_id,
            )
        )
        return _conversation(row) if row else None

    def list_messages(self, *, conversation_id: str) -> list[MessageRecord]:
        rows = self._session.scalars(
            select(MessageRow)
            .where(MessageRow.conversation_id == conversation_id)
            .order_by(MessageRow.created_at.asc(), MessageRow.id.asc())
        ).all()
        return [_message(row) for row in rows]

    def append_message(self, message: MessageRecord) -> MessageRecord:
        row = MessageRow(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            route=message.route,
            status=message.status,
            provider=message.provider,
            model=message.model,
            created_at=message.created_at,
        )
        self._session.add(row)
        self._session.commit()
        return message


def _project(row: ProjectRow) -> ProjectRecord:
    return ProjectRecord(
        id=row.id,
        name=row.name,
        owner_user_id=row.owner_user_id,
        created_at=row.created_at,
    )


def _conversation(row: ConversationRow) -> ConversationRecord:
    return ConversationRecord(
        id=row.id,
        project_id=row.project_id,
        owner_user_id=row.owner_user_id,
        title=row.title,
        created_at=row.created_at,
    )


def _message(row: MessageRow) -> MessageRecord:
    return MessageRecord(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        created_at=row.created_at,
        route=row.route,
        status=row.status,
        provider=row.provider,
        model=row.model,
    )
