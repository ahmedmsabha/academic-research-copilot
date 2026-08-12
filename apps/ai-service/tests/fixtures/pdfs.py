"""Helpers to build tiny synthetic PDFs for tests."""

from __future__ import annotations


def make_text_pdf(text: str, *, page2: str | None = None) -> bytes:
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    if page2:
        second = document.new_page()
        second.insert_text((72, 72), page2)
    data = document.tobytes()
    document.close()
    return data
