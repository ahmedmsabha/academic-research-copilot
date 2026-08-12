"""Unit tests for document overview query detection."""

from app.rag.retrieval import is_document_overview_query


def test_overview_queries_detected() -> None:
    assert is_document_overview_query("Summarize the research attached")
    assert is_document_overview_query("Give me an overview of this paper")
    assert is_document_overview_query("What are the main findings?")
    assert is_document_overview_query("Tell me about the uploaded document")


def test_specific_queries_not_treated_as_overview() -> None:
    assert not is_document_overview_query("What do neural embeddings map text to?")
    assert not is_document_overview_query("What is the capital of Mars?")
