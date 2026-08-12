"""Retrieval helpers for grounded document answers."""

from __future__ import annotations

import re

# Meta questions about the uploaded file itself rarely share tokens with paper body text.
_OVERVIEW_RE = re.compile(
    r"(?is)"
    r"("
    r"\bsummar(?:y|ize|ise|ising|izing)\b|"
    r"\boverview\b|"
    r"\bmain\s+(?:points?|findings?|ideas?|claims?|results?)\b|"
    r"\bkey\s+(?:points?|findings?|takeaways?)\b|"
    r"\btl;?dr\b|"
    r"\bwhat\s+(?:is|are|does)\s+(?:this|the)\s+"
    r"(?:paper|document|research|pdf|file|article|study)\b|"
    r"\btell\s+me\s+about\s+(?:this|the|my)\s+"
    r"(?:paper|document|research|pdf|file|article|study)\b|"
    r"\b(?:this|the|my|attached|uploaded)\s+"
    r"(?:paper|document|research|pdf|file|article|study)\b|"
    r"\bresearch\s+attached\b|"
    r"\battached\s+(?:research|document|paper|pdf|file)\b"
    r")"
)


def is_document_overview_query(question: str) -> bool:
    """True when the user is asking about the uploaded document as a whole."""
    cleaned = question.strip()
    if not cleaned:
        return False
    return _OVERVIEW_RE.search(cleaned) is not None
