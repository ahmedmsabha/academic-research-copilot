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


def make_image_only_pdf(label: str = "SCANNED PAGE") -> bytes:
    """PDF whose only content is a raster image — no extractable text layer."""
    import pymupdf

    source = pymupdf.open()
    source_page = source.new_page()
    source_page.insert_text((72, 72), label)
    pixmap = source_page.get_pixmap()

    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(page.rect, pixmap=pixmap)
    data = document.tobytes()
    document.close()
    source.close()
    return data
