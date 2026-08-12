"""Citation formatting from retrieval metadata (never from free-form model text)."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import CitationResponse


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    content: str
    page_start: int | None
    page_end: int | None
    score: float
    ordinal: int


def format_page_label(filename: str, page_start: int | None, page_end: int | None) -> str:
    if page_start is None:
        return filename
    if page_end is None or page_end == page_start:
        return f"{filename}, p. {page_start}"
    return f"{filename}, pp. {page_start}–{page_end}"


def citations_from_chunks(chunks: list[RetrievedChunk]) -> list[CitationResponse]:
    seen: set[tuple[str, int | None, int | None]] = set()
    citations: list[CitationResponse] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.page_start, chunk.page_end)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            CitationResponse(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                filename=chunk.filename,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                label=format_page_label(chunk.filename, chunk.page_start, chunk.page_end),
            )
        )
    return citations


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        cite = format_page_label(chunk.filename, chunk.page_start, chunk.page_end)
        parts.append(f"[{index}] Source: {cite}\n{chunk.content}")
    return "\n\n".join(parts)
