"""Postgres-backed store using Prisma-managed tables + pgvector."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ConversationRow, DocumentChunkRow, DocumentRow, MessageRow, ProjectRow
from app.rag.citations import RetrievedChunk
from app.repositories.memory_store import (
    ChunkRecord,
    ConversationRecord,
    DocumentRecord,
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
            citations_json=message.citations_json,
            created_at=message.created_at,
        )
        self._session.add(row)
        self._session.commit()
        return message

    def count_documents(self, *, project_id: str) -> int:
        rows = self._session.scalars(
            select(DocumentRow.id).where(DocumentRow.project_id == project_id)
        ).all()
        return len(rows)

    def create_document(self, document: DocumentRecord) -> DocumentRecord:
        row = DocumentRow(
            id=document.id,
            project_id=document.project_id,
            owner_user_id=document.owner_user_id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            checksum=document.checksum,
            storage_key=document.storage_key,
            page_count=document.page_count,
            status=document.status,
            failure_code=document.failure_code,
            failure_message=document.failure_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _document(row)

    def list_documents(self, *, project_id: str, owner_user_id: str) -> list[DocumentRecord]:
        rows = self._session.scalars(
            select(DocumentRow)
            .where(
                DocumentRow.project_id == project_id,
                DocumentRow.owner_user_id == owner_user_id,
            )
            .order_by(DocumentRow.created_at.desc())
        ).all()
        return [_document(row) for row in rows]

    def get_document(
        self,
        *,
        project_id: str,
        document_id: str,
        owner_user_id: str,
    ) -> DocumentRecord | None:
        row = self._session.scalar(
            select(DocumentRow).where(
                DocumentRow.id == document_id,
                DocumentRow.project_id == project_id,
                DocumentRow.owner_user_id == owner_user_id,
            )
        )
        return _document(row) if row else None

    def update_document(self, document: DocumentRecord) -> DocumentRecord:
        row = self._session.scalar(select(DocumentRow).where(DocumentRow.id == document.id))
        if row is None:
            raise RuntimeError("Document missing during update.")
        row.filename = document.filename
        row.content_type = document.content_type
        row.size_bytes = document.size_bytes
        row.checksum = document.checksum
        row.storage_key = document.storage_key
        row.page_count = document.page_count
        row.status = document.status
        row.failure_code = document.failure_code
        row.failure_message = document.failure_message
        row.updated_at = utc_now()
        self._session.commit()
        self._session.refresh(row)
        return _document(row)

    def delete_document(
        self,
        *,
        project_id: str,
        document_id: str,
        owner_user_id: str,
    ) -> DocumentRecord | None:
        row = self._session.scalar(
            select(DocumentRow).where(
                DocumentRow.id == document_id,
                DocumentRow.project_id == project_id,
                DocumentRow.owner_user_id == owner_user_id,
            )
        )
        if row is None:
            return None
        record = _document(row)
        self._session.delete(row)
        self._session.commit()
        return record

    def replace_chunks(self, *, document_id: str, chunks: list[ChunkRecord]) -> None:
        self._session.execute(
            delete(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
        )
        for chunk in chunks:
            self._session.add(
                DocumentChunkRow(
                    id=chunk.id,
                    project_id=chunk.project_id,
                    document_id=chunk.document_id,
                    ordinal=chunk.ordinal,
                    content=chunk.content,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    embedding_model=chunk.embedding_model,
                    embedding_dimension=chunk.embedding_dimension,
                    embedding=chunk.embedding,
                    created_at=chunk.created_at,
                )
            )
        self._session.commit()

    def delete_chunks_for_document(self, *, document_id: str) -> None:
        self._session.execute(
            delete(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
        )
        self._session.commit()

    def has_ready_documents(self, *, project_id: str) -> bool:
        row = self._session.scalar(
            select(DocumentRow.id).where(
                DocumentRow.project_id == project_id,
                DocumentRow.status == "ready",
            )
        )
        return row is not None

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
        distance = DocumentChunkRow.embedding.cosine_distance(query_embedding)
        rows = self._session.execute(
            select(
                DocumentChunkRow,
                DocumentRow.filename,
                distance.label("distance"),
            )
            .join(DocumentRow, DocumentRow.id == DocumentChunkRow.document_id)
            .where(
                DocumentChunkRow.project_id == project_id,
                DocumentRow.project_id == project_id,
                DocumentRow.status == "ready",
                DocumentChunkRow.embedding.is_not(None),
                DocumentChunkRow.embedding_model == embedding_model,
                DocumentChunkRow.embedding_dimension == embedding_dimension,
                distance <= max_distance,
            )
            .order_by(distance.asc(), DocumentChunkRow.ordinal.asc(), DocumentChunkRow.id.asc())
            .limit(top_k)
        ).all()

        results: list[RetrievedChunk] = []
        for chunk_row, filename, dist in rows:
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_row.id,
                    document_id=chunk_row.document_id,
                    filename=filename,
                    content=chunk_row.content,
                    page_start=chunk_row.page_start,
                    page_end=chunk_row.page_end,
                    score=float(dist),
                    ordinal=chunk_row.ordinal,
                )
            )
        return results

    def list_leading_chunks(
        self,
        *,
        project_id: str,
        embedding_model: str,
        embedding_dimension: int,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return early ordinal chunks from ready docs (for summarize/overview questions)."""
        rows = self._session.execute(
            select(DocumentChunkRow, DocumentRow.filename)
            .join(DocumentRow, DocumentRow.id == DocumentChunkRow.document_id)
            .where(
                DocumentChunkRow.project_id == project_id,
                DocumentRow.project_id == project_id,
                DocumentRow.status == "ready",
                DocumentChunkRow.embedding.is_not(None),
                DocumentChunkRow.embedding_model == embedding_model,
                DocumentChunkRow.embedding_dimension == embedding_dimension,
            )
            .order_by(
                DocumentRow.created_at.asc(),
                DocumentChunkRow.ordinal.asc(),
                DocumentChunkRow.id.asc(),
            )
            .limit(top_k)
        ).all()

        return [
            RetrievedChunk(
                chunk_id=chunk_row.id,
                document_id=chunk_row.document_id,
                filename=filename,
                content=chunk_row.content,
                page_start=chunk_row.page_start,
                page_end=chunk_row.page_end,
                score=1.0,
                ordinal=chunk_row.ordinal,
            )
            for chunk_row, filename in rows
        ]


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
        citations_json=row.citations_json,
    )


def _document(row: DocumentRow) -> DocumentRecord:
    return DocumentRecord(
        id=row.id,
        project_id=row.project_id,
        owner_user_id=row.owner_user_id,
        filename=row.filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        checksum=row.checksum,
        storage_key=row.storage_key,
        page_count=row.page_count,
        status=row.status,
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
