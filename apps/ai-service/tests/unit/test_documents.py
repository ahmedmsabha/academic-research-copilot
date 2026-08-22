"""Document retry and not-ready chat copy."""

from __future__ import annotations

import pytest

from app.api.v1.documents import _index_in_background
from app.core.config import get_settings
from app.core.errors import DocumentProcessingError
from app.providers.embeddings import FakeEmbeddingProvider
from app.providers.storage import LocalObjectStorage
from app.repositories.memory_store import (
    DocumentRecord,
    MemoryStore,
    get_store,
    reset_store,
    utc_now,
)
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


async def test_index_missing_pdf_marks_failed(tmp_path) -> None:
    store = MemoryStore()
    project = store.create_project(owner_user_id="user-1", name="Demo")
    document = _document(status="queued")
    document.project_id = project.id
    document.storage_key = "user-1/proj-1/missing.pdf"
    store.create_document(document)

    service = DocumentService(
        store,
        LocalObjectStorage(tmp_path / "uploads"),
        FakeEmbeddingProvider(dimension=8),
        get_settings(),
    )
    with pytest.raises(DocumentProcessingError):
        await service.index_document(
            owner_user_id="user-1",
            project_id=project.id,
            document_id=document.id,
        )

    failed = store.get_document(
        project_id=project.id,
        document_id=document.id,
        owner_user_id="user-1",
    )
    assert failed is not None
    assert failed.status == "failed"
    assert failed.failure_message is not None
    assert "missing from storage" in failed.failure_message


async def test_background_index_missing_pdf_marks_failed() -> None:
    reset_store()
    store = get_store()
    project = store.create_project(owner_user_id="user-1", name="Demo")
    document = _document(status="queued")
    document.project_id = project.id
    document.storage_key = "user-1/missing/doc.pdf"
    store.create_document(document)

    await _index_in_background(
        owner_user_id="user-1",
        project_id=project.id,
        document_id=document.id,
        settings=get_settings(),
    )

    failed = store.get_document(
        project_id=project.id,
        document_id=document.id,
        owner_user_id="user-1",
    )
    assert failed is not None
    assert failed.status == "failed"
    reset_store()
