"""In-memory store for Task 1.

History survives browser refresh while the AI service process stays up.
Task 2 replaces this with PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ProjectRecord:
    id: str
    name: str
    owner_user_id: str
    created_at: datetime


@dataclass
class ConversationRecord:
    id: str
    project_id: str
    owner_user_id: str
    title: str
    created_at: datetime


@dataclass
class MessageRecord:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    route: str | None = None
    status: str | None = None
    provider: str | None = None
    model: str | None = None


@dataclass
class MemoryStore:
    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    conversations: dict[str, ConversationRecord] = field(default_factory=dict)
    messages: dict[str, list[MessageRecord]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def create_project(self, *, owner_user_id: str, name: str) -> ProjectRecord:
        with self._lock:
            project = ProjectRecord(
                id=str(uuid4()),
                name=name.strip() or "My Research Project",
                owner_user_id=owner_user_id,
                created_at=utc_now(),
            )
            self.projects[project.id] = project
            return project

    def list_projects(self, *, owner_user_id: str) -> list[ProjectRecord]:
        with self._lock:
            items = [p for p in self.projects.values() if p.owner_user_id == owner_user_id]
            return sorted(items, key=lambda p: p.created_at)

    def get_project(self, *, project_id: str, owner_user_id: str) -> ProjectRecord | None:
        with self._lock:
            project = self.projects.get(project_id)
            if project is None or project.owner_user_id != owner_user_id:
                return None
            return project

    def create_conversation(
        self,
        *,
        project_id: str,
        owner_user_id: str,
        title: str,
    ) -> ConversationRecord:
        with self._lock:
            conversation = ConversationRecord(
                id=str(uuid4()),
                project_id=project_id,
                owner_user_id=owner_user_id,
                title=title.strip() or "New chat",
                created_at=utc_now(),
            )
            self.conversations[conversation.id] = conversation
            self.messages[conversation.id] = []
            return conversation

    def get_conversation(
        self,
        *,
        conversation_id: str,
        owner_user_id: str,
    ) -> ConversationRecord | None:
        with self._lock:
            conversation = self.conversations.get(conversation_id)
            if conversation is None or conversation.owner_user_id != owner_user_id:
                return None
            return conversation

    def list_messages(self, *, conversation_id: str) -> list[MessageRecord]:
        with self._lock:
            items = list(self.messages.get(conversation_id, []))
            return sorted(items, key=lambda m: (m.created_at, m.id))

    def append_message(self, message: MessageRecord) -> MessageRecord:
        with self._lock:
            bucket = self.messages.setdefault(message.conversation_id, [])
            bucket.append(message)
            return message


_store = MemoryStore()


def get_store() -> MemoryStore:
    return _store


def reset_store() -> MemoryStore:
    """Test helper to clear singleton state."""
    global _store
    _store = MemoryStore()
    return _store
