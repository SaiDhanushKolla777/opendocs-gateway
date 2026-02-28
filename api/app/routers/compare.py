"""Document comparison endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db_gen
from app.models import CompareRequest, CompareResponse
from app.db.repositories import get_document
from app.services.ingestion_service import document_to_chunks
from app.services.comparison_service import compare_documents
from app.services.metrics_service import LatencyTimer

router = APIRouter(tags=["compare"])


@router.post("/compare", response_model=CompareResponse)
async def compare(body: CompareRequest, db: Session = Depends(get_db_gen)):
    """Compare old vs new document version."""
    old_doc = get_document(db, body.old_document_id)
    new_doc = get_document(db, body.new_document_id)
    if not old_doc:
        raise HTTPException(404, "Old document not found")
    if not new_doc:
        raise HTTPException(404, "New document not found")
    old_chunks = document_to_chunks(db, body.old_document_id)
    new_chunks = document_to_chunks(db, body.new_document_id)
    if not old_chunks or not new_chunks:
        raise HTTPException(400, "One or both documents have no chunks")
    with LatencyTimer():
        summary, structured_changes, citations_old, citations_new = await compare_documents(
            old_chunks, new_chunks
        )
    return CompareResponse(
        summary=summary,
        structured_changes=structured_changes,
        citations_old=citations_old,
        citations_new=citations_new,
    )
