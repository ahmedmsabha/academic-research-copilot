"""PDF text extraction with page boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    pages: list[ExtractedPage]
    page_count: int


PDF_MAGIC = b"%PDF-"


def looks_like_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def normalize_whitespace(text: str) -> str:
    cleaned = text.replace("\x00", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_text(data: bytes) -> ExtractedDocument:
    """Extract page-aware text using PyMuPDF."""
    import pymupdf

    if not looks_like_pdf(data):
        raise ValueError("File is not a valid PDF.")

    pages: list[ExtractedPage] = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for index, page in enumerate(document, start=1):
            raw = page.get_text("text") or ""
            text = normalize_whitespace(raw)
            pages.append(ExtractedPage(page_number=index, text=text))
        page_count = document.page_count

    return ExtractedDocument(pages=pages, page_count=page_count)


def is_near_empty(extracted: ExtractedDocument, *, min_chars: int = 40) -> bool:
    total = sum(len(page.text) for page in extracted.pages)
    return total < min_chars
