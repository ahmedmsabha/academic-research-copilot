"""Project-scoped document upload and management routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import (
    Store,
    _build_default_embeddings,
    _build_default_storage,
    get_document_service,
)
from app.core.config import Settings, get_settings
from app.core.security import require_user_id
from app.models.schemas import DocumentResponse
from app.repositories.memory_store import DocumentRecord, get_store
from app.repositories.postgres_store import PostgresStore
from app.services.documents import DocumentService

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])
logger = logging.getLogger(__name__)

_INTERRUPTED_STATUSES = {
    "queued",
    "extracting",
    "chunking",
    "embedding",
    "indexing",
}
_RECOVERY_INTERVAL_SECONDS = 15
_INDEX_TASKS: set[asyncio.Task[None]] = set()
_IN_FLIGHT: set[str] = set()
_IN_FLIGHT_LOCK = asyncio.Lock()


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    project_id: str,
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    return service.list_documents(owner_user_id=user_id, project_id=project_id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    project_id: str,
    document_id: str,
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return service.get_document(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document_id,
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    data = await file.read()
    document = await service.upload_document(
        owner_user_id=user_id,
        project_id=project_id,
        filename=file.filename or "document.pdf",
        content_type=file.content_type,
        data=data,
    )
    # Tests index synchronously for deterministic assertions; otherwise queue background work.
    if settings.app_env == "test":
        return await service.index_document(
            owner_user_id=user_id,
            project_id=project_id,
            document_id=document.id,
        )

    schedule_document_index(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document.id,
        settings=settings,
    )
    return document


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(
    project_id: str,
    document_id: str,
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    document = service.queue_document_retry(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document_id,
    )
    if document.status == "ready":
        return document

    if settings.app_env == "test":
        return await service.index_document(
            owner_user_id=user_id,
            project_id=project_id,
            document_id=document.id,
        )

    schedule_document_index(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document.id,
        settings=settings,
    )
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    project_id: str,
    document_id: str,
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
) -> None:
    await service.delete_document(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document_id,
    )


def schedule_document_index(
    *,
    owner_user_id: str,
    project_id: str,
    document_id: str,
    settings: Settings,
) -> None:
    """Index off the request so a closed Next.js proxy connection cannot cancel the job."""
    if settings.app_env == "test":
        return
    task = asyncio.create_task(
        _index_in_background(
            owner_user_id=owner_user_id,
            project_id=project_id,
            document_id=document_id,
            settings=settings,
        ),
        name=f"index-document-{document_id}",
    )
    _INDEX_TASKS.add(task)
    task.add_done_callback(_INDEX_TASKS.discard)


async def _index_in_background(
    *,
    owner_user_id: str,
    project_id: str,
    document_id: str,
    settings: Settings,
) -> None:
    """Create a fresh store/session for background indexing after the request ends."""
    async with _IN_FLIGHT_LOCK:
        if document_id in _IN_FLIGHT:
            return
        _IN_FLIGHT.add(document_id)

    try:
        storage = _build_default_storage()
        embeddings = _build_default_embeddings()

        if settings.app_env == "test" or not settings.database_url:
            store: Store = get_store()
            service = DocumentService(store, storage, embeddings, settings)
            await service.index_document(
                owner_user_id=owner_user_id,
                project_id=project_id,
                document_id=document_id,
            )
            return

        from app.db.session import get_session_factory

        session = get_session_factory()()
        try:
            store = PostgresStore(session)
            service = DocumentService(store, storage, embeddings, settings)
            await service.index_document(
                owner_user_id=owner_user_id,
                project_id=project_id,
                document_id=document_id,
            )
        finally:
            session.close()
    except Exception:
        logger.exception(
            "document_background_index_failed",
            extra={"document_id": document_id, "project_id": project_id},
        )
    finally:
        _IN_FLIGHT.discard(document_id)


async def recover_interrupted_indexing(settings: Settings) -> None:
    """Restart index jobs left mid-pipeline after a deploy, host sleep, or cancelled request."""
    if settings.app_env == "test":
        return

    try:
        interrupted = _list_interrupted_documents(settings)
    except Exception:
        logger.exception("document_index_recovery_list_failed")
        return

    pending = [document for document in interrupted if document.id not in _IN_FLIGHT]
    if not pending:
        return

    logger.info(
        "recovering_interrupted_indexing",
        extra={"count": len(pending)},
    )
    for document in pending:
        schedule_document_index(
            owner_user_id=document.owner_user_id,
            project_id=document.project_id,
            document_id=document.id,
            settings=settings,
        )


async def run_indexing_recovery_loop(settings: Settings) -> None:
    """Pick up queued/stuck documents while the process is alive — not only on startup."""
    if settings.app_env == "test":
        return
    await recover_interrupted_indexing(settings)
    while True:
        await asyncio.sleep(_RECOVERY_INTERVAL_SECONDS)
        await recover_interrupted_indexing(settings)


def _list_interrupted_documents(settings: Settings) -> list[DocumentRecord]:
    if not settings.database_url:
        store: Store = get_store()
        return store.list_documents_by_statuses(statuses=_INTERRUPTED_STATUSES)

    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        store = PostgresStore(session)
        return store.list_documents_by_statuses(statuses=_INTERRUPTED_STATUSES)
    finally:
        session.close()
