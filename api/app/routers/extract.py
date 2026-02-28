"""Structured extraction endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_db_gen
from app.models import ExtractRequest, ExtractResponse
from app.db.repositories import get_document
from app.services.ingestion_service import document_to_chunks
from app.services.extraction_service import extract_structured
from app.services.metrics_service import LatencyTimer

router = APIRouter(tags=["extract"])


def _sample_spread(chunks, max_count: int):
    """Sample chunks evenly spread across the document for broad coverage."""
    if len(chunks) <= max_count:
        return chunks
    step = len(chunks) / max_count
    return [chunks[int(i * step)] for i in range(max_count)]


@router.post("/documents/{document_id}/extract", response_model=ExtractResponse)
async def extract(
    document_id: str,
    body: ExtractRequest,
    db: Session = Depends(get_db_gen),
):
    """Extract structured data from document."""
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    chunks = document_to_chunks(db, document_id)
    if not chunks:
        raise HTTPException(400, "Document has no chunks")

    sampled = _sample_spread(chunks, 15)

    schema_desc = (body.schema_request or {}).get("description") if isinstance(body.schema_request, dict) else None
    with LatencyTimer():
        data, citations, status = await extract_structured(sampled, schema_desc)
    from app.services.metrics_service import record_schema_result
    record_schema_result(status == "valid")
    return ExtractResponse(data=data, citations=citations, validation_status=status)
