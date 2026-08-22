"""Document upload, indexing, and cleanup use cases."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import PurePosixPath
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import (
    DocumentProcessingError,
    DocumentTooLargeError,
    NotFoundError,
    ProjectDocumentLimitError,
    ProviderConfigError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnsupportedDocumentError,
    ValidationAppError,
)
from app.models.schemas import DocumentResponse
from app.providers.embeddings import EmbeddingProvider
from app.providers.storage import ObjectStorage
from app.rag.chunking import chunk_extracted_document
from app.rag.extract import (
    PdfOcrUnavailableError,
    extract_pdf_text,
    is_near_empty,
    looks_like_pdf,
)
from app.repositories.memory_store import ChunkRecord, DocumentRecord, MemoryStore, utc_now
from app.repositories.postgres_store import PostgresStore

logger = logging.getLogger(__name__)

Store = MemoryStore | PostgresStore

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentService:
    def __init__(
        self,
        store: Store,
        storage: ObjectStorage,
        embeddings: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self._store = store
        self._storage = storage
        self._embeddings = embeddings
        self._settings = settings

    def list_documents(self, *, owner_user_id: str, project_id: str) -> list[DocumentResponse]:
        self._require_project(owner_user_id=owner_user_id, project_id=project_id)
        records = self._store.list_documents(project_id=project_id, owner_user_id=owner_user_id)
        return [_to_response(record) for record in records]

    def get_document(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        document_id: str,
    ) -> DocumentResponse:
        document = self._store.get_document(
            project_id=project_id,
            document_id=document_id,
            owner_user_id=owner_user_id,
        )
        if document is None:
            raise NotFoundError("Document not found.")
        return _to_response(document)

    async def upload_document(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> DocumentResponse:
        self._require_project(owner_user_id=owner_user_id, project_id=project_id)
        self._validate_upload(filename=filename, content_type=content_type, data=data)

        limit = self._settings.max_documents_per_project
        if self._store.count_documents(project_id=project_id) >= limit:
            raise ProjectDocumentLimitError()

        document_id = str(uuid4())
        safe_name = _safe_display_filename(filename)
        object_key = f"{owner_user_id}/{project_id}/{document_id}.pdf"
        checksum = hashlib.sha256(data).hexdigest()

        await self._storage.put_pdf(
            object_key=object_key,
            data=data,
            content_type="application/pdf",
        )

        now = utc_now()
        record = DocumentRecord(
            id=document_id,
            project_id=project_id,
            owner_user_id=owner_user_id,
            filename=safe_name,
            content_type="application/pdf",
            size_bytes=len(data),
            checksum=checksum,
            storage_key=object_key,
            page_count=None,
            status="queued",
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
        self._store.create_document(record)
        return _to_response(record)

    async def index_document(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        document_id: str,
    ) -> DocumentResponse:
        document = self._store.get_document(
            project_id=project_id,
            document_id=document_id,
            owner_user_id=owner_user_id,
        )
        if document is None:
            raise NotFoundError("Document not found.")

        try:
            await self._run_pipeline(document)
        except Exception as exc:  # noqa: BLE001 — map to safe failure state
            logger.exception(
                "document_indexing_failed",
                extra={
                    "document_id": document_id,
                    "project_id": project_id,
                },
            )
            document.status = "failed"
            document.failure_code = getattr(exc, "code", None) or "DOCUMENT_PROCESSING_ERROR"
            document.failure_message = _safe_failure_message(exc)
            self._store.update_document(document)
            self._store.delete_chunks_for_document(document_id=document.id)
            raise DocumentProcessingError(document.failure_message) from None

        refreshed = self._store.get_document(
            project_id=project_id,
            document_id=document_id,
            owner_user_id=owner_user_id,
        )
        if refreshed is None:
            raise NotFoundError("Document not found.")
        return _to_response(refreshed)

    def queue_document_retry(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        document_id: str,
    ) -> DocumentResponse:
        """Reset a failed/uploaded document to queued without indexing yet."""
        document = self._store.get_document(
            project_id=project_id,
            document_id=document_id,
            owner_user_id=owner_user_id,
        )
        if document is None:
            raise NotFoundError("Document not found.")
        if document.status == "ready":
            return _to_response(document)
        # Allow retry of mid-pipeline statuses. After a deploy or host sleep the
        # FastAPI BackgroundTask is gone, but the row can stay on embedding forever.

        document.status = "queued"
        document.failure_code = None
        document.failure_message = None
        self._store.update_document(document)
        self._store.delete_chunks_for_document(document_id=document.id)
        return _to_response(document)

    async def retry_document(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        document_id: str,
    ) -> DocumentResponse:
        """Synchronously re-index (used by tests). Prefer queue + background in HTTP."""
        queued = self.queue_document_retry(
            owner_user_id=owner_user_id,
            project_id=project_id,
            document_id=document_id,
        )
        if queued.status == "ready":
            return queued
        try:
            return await self.index_document(
                owner_user_id=owner_user_id,
                project_id=project_id,
                document_id=document_id,
            )
        except DocumentProcessingError:
            # Persist failure state for the UI; return the failed document instead of 422.
            failed = self._store.get_document(
                project_id=project_id,
                document_id=document_id,
                owner_user_id=owner_user_id,
            )
            if failed is None:
                raise
            return _to_response(failed)

    async def delete_document(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        document_id: str,
    ) -> None:
        document = self._store.delete_document(
            project_id=project_id,
            document_id=document_id,
            owner_user_id=owner_user_id,
        )
        if document is None:
            raise NotFoundError("Document not found.")
        try:
            await self._storage.delete_object(object_key=document.storage_key)
        except Exception:  # noqa: BLE001
            logger.exception(
                "document_storage_cleanup_failed",
                extra={"document_id": document_id, "project_id": project_id},
            )

    async def _run_pipeline(self, document: DocumentRecord) -> None:
        document.status = "extracting"
        document.failure_code = None
        document.failure_message = None
        self._store.update_document(document)

        pdf_bytes = await self._storage.get_pdf(object_key=document.storage_key)
        try:
            extracted = await asyncio.to_thread(
                extract_pdf_text,
                pdf_bytes,
                ocr=self._settings.enable_ocr,
                ocr_language=self._settings.ocr_language,
                ocr_dpi=self._settings.ocr_dpi,
            )
        except PdfOcrUnavailableError:
            raise DocumentProcessingError(
                "This PDF looks like a scan (no text layer). OCR needs Tesseract "
                "on the server. Upload a text-based PDF — for example a Word/Google "
                "Docs export or an arXiv paper — or redeploy with Tesseract and "
                "click Retry indexing."
            ) from None
        document.page_count = extracted.page_count
        if is_near_empty(extracted):
            raise DocumentProcessingError(
                "No extractable text was found in this PDF. "
                "If this is a photo or scan, try a clearer copy, or upload a PDF "
                "that already contains a text layer."
            )

        document.status = "chunking"
        self._store.update_document(document)
        text_chunks = chunk_extracted_document(
            extracted,
            chunk_size=self._settings.chunk_size_chars,
            overlap=self._settings.chunk_overlap_chars,
        )
        if not text_chunks:
            raise DocumentProcessingError("Unable to create text chunks from this PDF.")
        max_chunks = self._settings.max_index_chunks
        if len(text_chunks) > max_chunks:
            raise DocumentProcessingError(
                f"This PDF is too long to index ({len(text_chunks)} text chunks, "
                f"limit {max_chunks}). Upload a shorter paper or a single chapter "
                "(about 40 pages or fewer), then ask again."
            )

        document.status = "embedding"
        self._store.update_document(document)
        embedding_response = await self._embeddings.embed([chunk.content for chunk in text_chunks])
        if len(embedding_response.vectors) != len(text_chunks):
            raise DocumentProcessingError("Embedding generation returned an unexpected result.")

        document.status = "indexing"
        self._store.update_document(document)
        now = utc_now()
        chunk_records = [
            ChunkRecord(
                id=str(uuid4()),
                project_id=document.project_id,
                document_id=document.id,
                ordinal=chunk.ordinal,
                content=chunk.content,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                embedding_model=embedding_response.model,
                embedding_dimension=embedding_response.dimension,
                embedding=vector,
                created_at=now,
                filename=document.filename,
            )
            for chunk, vector in zip(text_chunks, embedding_response.vectors, strict=True)
        ]
        self._store.replace_chunks(document_id=document.id, chunks=chunk_records)

        document.status = "ready"
        document.failure_code = None
        document.failure_message = None
        self._store.update_document(document)

    def _require_project(self, *, owner_user_id: str, project_id: str) -> None:
        project = self._store.get_project(project_id=project_id, owner_user_id=owner_user_id)
        if project is None:
            raise NotFoundError("Project not found.")

    def _validate_upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> None:
        if not data:
            raise ValidationAppError("Uploaded file is empty.")
        if len(data) > self._settings.max_upload_bytes:
            raise DocumentTooLargeError(
                f"File exceeds the maximum size of {self._settings.max_upload_bytes} bytes."
            )
        lowered = filename.lower()
        declared = (content_type or "").lower()
        if not lowered.endswith(".pdf") and "pdf" not in declared:
            raise UnsupportedDocumentError()
        if not looks_like_pdf(data):
            raise UnsupportedDocumentError("File content is not a valid PDF.")


def _safe_display_filename(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name.strip() or "document.pdf"
    cleaned = SAFE_FILENAME_RE.sub("_", name)
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned[:180]


def _safe_failure_message(exc: Exception) -> str:
    if isinstance(
        exc,
        (
            DocumentProcessingError,
            ProviderUnavailableError,
            ProviderTimeoutError,
            ProviderConfigError,
        ),
    ):
        return exc.message
    return "Document processing failed. You can retry indexing."


def _to_response(document: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        project_id=document.project_id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        status=document.status,  # type: ignore[arg-type]
        failure_code=document.failure_code,
        failure_message=document.failure_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
