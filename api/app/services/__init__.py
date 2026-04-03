"""Services."""
from .comparison_service import compare_documents
from .extraction_service import extract_structured
from .ingestion_service import document_to_chunks, ingest_document
from .llm_service import chat_completion, get_llm_client
from .metrics_service import get_metrics, LatencyTimer, record_request_end, record_request_start
from .report_service import create_report, export_report_json, get_report
from .retrieval_service import (
    chunks_to_citations,
    format_context_with_labels,
    score_chunks,
    select_top_chunks,
    tfidf_scores_parallel,
)

__all__ = [
    "chat_completion",
    "get_llm_client",
    "ingest_document",
    "document_to_chunks",
    "score_chunks",
    "tfidf_scores_parallel",
    "select_top_chunks",
    "chunks_to_citations",
    "format_context_with_labels",
    "extract_structured",
    "compare_documents",
    "create_report",
    "get_report",
    "export_report_json",
    "get_metrics",
    "LatencyTimer",
    "record_request_start",
    "record_request_end",
]
