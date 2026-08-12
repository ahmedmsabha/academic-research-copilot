"""Unit tests for PDF chunking and citation formatting."""

from __future__ import annotations

from app.rag.chunking import chunk_extracted_document
from app.rag.citations import RetrievedChunk, citations_from_chunks, format_page_label
from app.rag.extract import ExtractedDocument, ExtractedPage, normalize_whitespace


def test_normalize_whitespace_collapses_runs() -> None:
    assert normalize_whitespace("hello   world\n\n\nnext") == "hello world\n\nnext"


def test_chunking_preserves_page_ranges() -> None:
    extracted = ExtractedDocument(
        pages=[
            ExtractedPage(page_number=1, text="Alpha " * 40),
            ExtractedPage(page_number=2, text="Beta " * 40),
        ],
        page_count=2,
    )
    chunks = chunk_extracted_document(extracted, chunk_size=120, overlap=20)
    assert chunks
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert all(chunk.content for chunk in chunks)


def test_citation_labels() -> None:
    assert format_page_label("paper.pdf", 3, 3) == "paper.pdf, p. 3"
    assert format_page_label("paper.pdf", 3, 5) == "paper.pdf, pp. 3–5"
    citations = citations_from_chunks(
        [
            RetrievedChunk(
                chunk_id="c1",
                document_id="d1",
                filename="paper.pdf",
                content="text",
                page_start=2,
                page_end=2,
                score=0.1,
                ordinal=0,
            ),
            RetrievedChunk(
                chunk_id="c2",
                document_id="d1",
                filename="paper.pdf",
                content="more",
                page_start=2,
                page_end=2,
                score=0.2,
                ordinal=1,
            ),
        ]
    )
    assert len(citations) == 1
    assert citations[0].label == "paper.pdf, p. 2"
