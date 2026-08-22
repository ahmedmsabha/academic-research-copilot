"""PDF extraction and OCR fallback."""

from __future__ import annotations

import pytest

from app.rag.extract import (
    PdfOcrUnavailableError,
    extract_pdf_text,
    is_near_empty,
)
from tests.fixtures.pdfs import make_image_only_pdf, make_text_pdf


def test_text_pdf_extracts_page_aware_content() -> None:
    pdf = make_text_pdf("Neural embeddings map text to vectors.", page2="Page two notes.")
    extracted = extract_pdf_text(pdf, ocr=False)
    assert extracted.page_count == 2
    assert "neural embeddings" in extracted.pages[0].text.lower()
    assert extracted.pages[1].page_number == 2
    assert not is_near_empty(extracted)


def test_image_only_pdf_is_near_empty_without_ocr() -> None:
    pdf = make_image_only_pdf("Lecture notes that only exist as pixels.")
    extracted = extract_pdf_text(pdf, ocr=False)
    assert extracted.page_count == 1
    assert is_near_empty(extracted)


def test_ocr_fallback_uses_recognized_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.rag.extract._ocr_page_text",
        lambda page, **kwargs: "OCR recovered lecture notes about photosynthesis.",
    )
    monkeypatch.setattr("app.rag.extract.shutil.which", lambda name: "/usr/bin/tesseract")
    pdf = make_image_only_pdf("hidden")
    extracted = extract_pdf_text(pdf, ocr=True)
    assert not is_near_empty(extracted)
    assert "photosynthesis" in extracted.pages[0].text.lower()


def test_ocr_unavailable_without_tesseract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.rag.extract.shutil.which", lambda name: None)
    pdf = make_image_only_pdf("hidden")
    with pytest.raises(PdfOcrUnavailableError):
        extract_pdf_text(pdf, ocr=True)
