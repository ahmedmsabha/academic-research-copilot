"""Document retry and not-ready chat copy."""

from __future__ import annotations

from app.core.config import get_settings
from app.providers.embeddings import FakeEmbeddingProvider
from app.providers.storage import LocalObjectStorage
from app.repositories.memory_store import DocumentRecord, MemoryStore, utc_now
from app.services.chat import _rag_not_ready_reply
from app.services.documents import DocumentService


def _document(*, status: str) -> DocumentRecord:
    now = utc_now()
    return DocumentRecord(
        id="doc-1",
        project_id="proj-1",
        owner_user_id="user-1",
        filename="book.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        storage_key="user-1/proj-1/doc-1.pdf",
        status=status,
        created_at=now,
        updated_at=now,
        page_count=407,
    )


def test_queue_retry_resets_stuck_embedding(tmp_path) -> None:
    store = MemoryStore()
    store.create_project(owner_user_id="user-1", name="Demo")
    # Replace the generated project id with the fixture id used by the document.
    project = next(iter(store.projects.values()))
    document = _document(status="embedding")
    document.project_id = project.id
    store.create_document(document)

    service = DocumentService(
        store,
        LocalObjectStorage(tmp_path / "uploads"),
        FakeEmbeddingProvider(dimension=8),
        get_settings(),
    )
    queued = service.queue_document_retry(
        owner_user_id="user-1",
        project_id=project.id,
        document_id=document.id,
    )
    assert queued.status == "queued"


def test_rag_not_ready_reply_distinguishes_processing() -> None:
    assert "still being indexed" in _rag_not_ready_reply([_document(status="embedding")])
    assert "indexing failed" in _rag_not_ready_reply([_document(status="failed")]).lower()
    assert "upload a pdf" in _rag_not_ready_reply([]).lower()
