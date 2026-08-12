"""Page-aware text chunking with configurable size and overlap."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.extract import ExtractedDocument, ExtractedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    ordinal: int
    content: str
    page_start: int
    page_end: int
    char_start: int
    char_end: int


def chunk_extracted_document(
    extracted: ExtractedDocument,
    *,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size.")

    segments = _page_segments(extracted.pages)
    if not segments:
        return []

    chunks: list[TextChunk] = []
    start = 0
    ordinal = 0
    total_chars = len(segments)

    while start < total_chars:
        end = min(start + chunk_size, total_chars)
        # Prefer breaking on whitespace when we are not at the end.
        if end < total_chars:
            window = "".join(item.char for item in segments[start:end])
            break_at = max(window.rfind("\n"), window.rfind(" "))
            if break_at >= int(chunk_size * 0.5):
                end = start + break_at + 1

        slice_segments = segments[start:end]
        content = "".join(item.char for item in slice_segments).strip()
        if content:
            chunks.append(
                TextChunk(
                    ordinal=ordinal,
                    content=content,
                    page_start=slice_segments[0].page_number,
                    page_end=slice_segments[-1].page_number,
                    char_start=start,
                    char_end=end,
                )
            )
            ordinal += 1

        if end >= total_chars:
            break
        next_start = max(end - overlap, start + 1)
        start = next_start

    return chunks


@dataclass(frozen=True, slots=True)
class _CharSeg:
    char: str
    page_number: int


def _page_segments(pages: list[ExtractedPage]) -> list[_CharSeg]:
    segments: list[_CharSeg] = []
    for page in pages:
        if not page.text:
            continue
        if segments and segments[-1].char != "\n":
            segments.append(_CharSeg(char="\n", page_number=page.page_number))
            segments.append(_CharSeg(char="\n", page_number=page.page_number))
        for char in page.text:
            segments.append(_CharSeg(char=char, page_number=page.page_number))
    return segments
