"""In-memory store for tests and DATABASE_URL-less local runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from app.rag.citations import RetrievedChunk
from app.rag.similarity import cosine_distance


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
    citations_json: str | None = None


@dataclass
class DocumentRecord:
    id: str
    project_id: str
    owner_user_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    status: str
    created_at: datetime
    updated_at: datetime
    checksum: str | None = None
    page_count: int | None = None
    failure_code: str | None = None
    failure_message: str | None = None


@dataclass
class ChunkRecord:
    id: str
    project_id: str
    document_id: str
    ordinal: int
    content: str
    page_start: int | None
    page_end: int | None
    char_start: int | None
    char_end: int | None
    embedding_model: str
    embedding_dimension: int
    embedding: list[float] | None
    created_at: datetime
    filename: str = ""


@dataclass
class MemoryStore:
    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    conversations: dict[str, ConversationRecord] = field(default_factory=dict)
    messages: dict[str, list[MessageRecord]] = field(default_factory=dict)
    documents: dict[str, DocumentRecord] = field(default_factory=dict)
    chunks: dict[str, list[ChunkRecord]] = field(default_factory=dict)
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

    def count_documents(self, *, project_id: str) -> int:
        with self._lock:
            return sum(1 for doc in self.documents.values() if doc.project_id == project_id)

    def create_document(self, document: DocumentRecord) -> DocumentRecord:
        with self._lock:
            self.documents[document.id] = document
            self.chunks[document.id] = []
            return document

    def list_documents(self, *, project_id: str, owner_user_id: str) -> list[DocumentRecord]:
        with self._lock:
            items = [
                doc
                for doc in self.documents.values()
                if doc.project_id == project_id and doc.owner_user_id == owner_user_id
            ]
            return sorted(items, key=lambda d: d.created_at, reverse=True)

    def get_document(
        self,
        *,
        project_id: str,
        document_id: str,
        owner_user_id: str,
    ) -> DocumentRecord | None:
        with self._lock:
            document = self.documents.get(document_id)
            if (
                document is None
                or document.project_id != project_id
                or document.owner_user_id != owner_user_id
            ):
                return None
            return document

    def update_document(self, document: DocumentRecord) -> DocumentRecord:
        with self._lock:
            document.updated_at = utc_now()
            self.documents[document.id] = document
            return document

    def delete_document(
        self,
        *,
        project_id: str,
        document_id: str,
        owner_user_id: str,
    ) -> DocumentRecord | None:
        with self._lock:
            document = self.documents.get(document_id)
            if (
                document is None
                or document.project_id != project_id
                or document.owner_user_id != owner_user_id
            ):
                return None
            self.documents.pop(document_id, None)
            self.chunks.pop(document_id, None)
            return document

    def replace_chunks(self, *, document_id: str, chunks: list[ChunkRecord]) -> None:
        with self._lock:
            self.chunks[document_id] = list(chunks)

    def delete_chunks_for_document(self, *, document_id: str) -> None:
        with self._lock:
            self.chunks[document_id] = []

    def has_ready_documents(self, *, project_id: str) -> bool:
        with self._lock:
            return any(
                doc.project_id == project_id and doc.status == "ready"
                for doc in self.documents.values()
            )

    def search_chunks(
        self,
        *,
        project_id: str,
        query_embedding: list[float],
        embedding_model: str,
        embedding_dimension: int,
        top_k: int,
        max_distance: float,
    ) -> list[RetrievedChunk]:
        with self._lock:
            ready_ids = {
                doc.id
                for doc in self.documents.values()
                if doc.project_id == project_id and doc.status == "ready"
            }
            filenames = {
                doc.id: doc.filename
                for doc in self.documents.values()
                if doc.id in ready_ids
            }
            candidates: list[RetrievedChunk] = []
            for document_id in ready_ids:
                for chunk in self.chunks.get(document_id, []):
                    if chunk.embedding is None:
                        continue
                    if chunk.embedding_model != embedding_model:
                        continue
                    if chunk.embedding_dimension != embedding_dimension:
                        continue
                    distance = cosine_distance(query_embedding, chunk.embedding)
                    if distance > max_distance:
                        continue
                    candidates.append(
                        RetrievedChunk(
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            filename=filenames.get(chunk.document_id, chunk.filename),
                            content=chunk.content,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            score=distance,
                            ordinal=chunk.ordinal,
                        )
                    )
            candidates.sort(key=lambda item: (item.score, item.ordinal, item.chunk_id))
            return candidates[:top_k]

    def list_leading_chunks(
        self,
        *,
        project_id: str,
        embedding_model: str,
        embedding_dimension: int,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return early ordinal chunks from ready docs (for summarize/overview questions)."""
        with self._lock:
            ready_docs = sorted(
                (
                    doc
                    for doc in self.documents.values()
                    if doc.project_id == project_id and doc.status == "ready"
                ),
                key=lambda doc: (doc.created_at, doc.id),
            )
            results: list[RetrievedChunk] = []
            for document in ready_docs:
                for chunk in sorted(
                    self.chunks.get(document.id, []),
                    key=lambda item: (item.ordinal, item.id),
                ):
                    if chunk.embedding is None:
                        continue
                    if chunk.embedding_model != embedding_model:
                        continue
                    if chunk.embedding_dimension != embedding_dimension:
                        continue
                    results.append(
                        RetrievedChunk(
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            filename=document.filename,
                            content=chunk.content,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            score=1.0,
                            ordinal=chunk.ordinal,
                        )
                    )
                    if len(results) >= top_k:
                        return results
            return results


_store = MemoryStore()


def get_store() -> MemoryStore:
    return _store


def reset_store() -> MemoryStore:
    """Test helper to clear singleton state."""
    global _store
    _store = MemoryStore()
    return _store


def citations_to_json(citations: list[dict[str, object]] | None) -> str | None:
    if not citations:
        return None
    return json.dumps(citations)


def citations_from_json(raw: str | None) -> list[dict[str, object]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []
