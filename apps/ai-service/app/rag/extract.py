"""PDF text extraction with page boundaries and optional OCR fallback."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    pages: list[ExtractedPage]
    page_count: int


class PdfOcrUnavailableError(RuntimeError):
    """Tesseract is missing or cannot be invoked."""


PDF_MAGIC = b"%PDF-"

_TESSDATA_CANDIDATES = (
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
    "/opt/homebrew/share/tessdata",
    "/usr/local/share/tessdata",
)


def looks_like_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def normalize_whitespace(text: str) -> str:
    cleaned = text.replace("\x00", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_text(
    data: bytes,
    *,
    ocr: bool = False,
    ocr_language: str = "eng",
    ocr_dpi: int = 150,
) -> ExtractedDocument:
    """Extract page-aware text using PyMuPDF, then OCR if the text layer is empty."""
    if not looks_like_pdf(data):
        raise ValueError("File is not a valid PDF.")

    extracted = _extract_native(data)
    if not ocr or not is_near_empty(extracted):
        return extracted
    return _extract_with_ocr(data, language=ocr_language, dpi=ocr_dpi)


def is_near_empty(extracted: ExtractedDocument, *, min_chars: int = 40) -> bool:
    total = sum(len(page.text) for page in extracted.pages)
    return total < min_chars


def resolve_tessdata_prefix() -> str | None:
    env = os.environ.get("TESSDATA_PREFIX")
    if env and Path(env).is_dir():
        return env
    for candidate in _TESSDATA_CANDIDATES:
        if Path(candidate).is_dir():
            return candidate
    return None


def _extract_native(data: bytes) -> ExtractedDocument:
    import pymupdf

    pages: list[ExtractedPage] = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for index, page in enumerate(document, start=1):
            raw = page.get_text("text") or ""
            pages.append(ExtractedPage(page_number=index, text=normalize_whitespace(raw)))
        page_count = document.page_count
    return ExtractedDocument(pages=pages, page_count=page_count)


def _extract_with_ocr(data: bytes, *, language: str, dpi: int) -> ExtractedDocument:
    if shutil.which("tesseract") is None:
        raise PdfOcrUnavailableError("tesseract is not installed.")

    import pymupdf

    tessdata = resolve_tessdata_prefix()
    pages: list[ExtractedPage] = []
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            for index, page in enumerate(document, start=1):
                raw = _ocr_page_text(page, language=language, dpi=dpi, tessdata=tessdata)
                pages.append(ExtractedPage(page_number=index, text=normalize_whitespace(raw)))
            page_count = document.page_count
    except PdfOcrUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — map Tesseract/path failures to a safe class
        message = str(exc).lower()
        if "tesseract" in message or "tessdata" in message:
            raise PdfOcrUnavailableError(str(exc)) from exc
        raise
    return ExtractedDocument(pages=pages, page_count=page_count)


def _ocr_page_text(page: object, *, language: str, dpi: int, tessdata: str | None) -> str:
    textpage = page.get_textpage_ocr(  # type: ignore[union-attr]
        language=language,
        dpi=dpi,
        full=True,
        tessdata=tessdata,
    )
    return textpage.extractText() or ""
