"""Project-scoped document upload and management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from app.api.deps import (
    Store,
    _build_default_embeddings,
    _build_default_storage,
    get_document_service,
)
from app.core.config import Settings, get_settings
from app.core.security import require_user_id
from app.models.schemas import DocumentResponse
from app.repositories.memory_store import get_store
from app.repositories.postgres_store import PostgresStore
from app.services.documents import DocumentService

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        _index_in_background,
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
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_user_id),
    service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    document = service.queue_document_retry(
        owner_user_id=user_id,
        project_id=project_id,
        document_id=document_id,
    )
    if document.status == "ready" or document.status in {
        "extracting",
        "chunking",
        "embedding",
        "indexing",
    }:
        return document

    if settings.app_env == "test":
        return await service.index_document(
            owner_user_id=user_id,
            project_id=project_id,
            document_id=document.id,
        )

    background_tasks.add_task(
        _index_in_background,
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


async def _index_in_background(
    *,
    owner_user_id: str,
    project_id: str,
    document_id: str,
    settings: Settings,
) -> None:
    """Create a fresh store/session for background indexing after the request ends."""
    storage = _build_default_storage()
    embeddings = _build_default_embeddings()

    if settings.app_env == "test" or not settings.database_url:
        store: Store = get_store()
        service = DocumentService(store, storage, embeddings, settings)
        try:
            await service.index_document(
                owner_user_id=owner_user_id,
                project_id=project_id,
                document_id=document_id,
            )
        except Exception:
            return
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
    except Exception:
        return
    finally:
        session.close()
