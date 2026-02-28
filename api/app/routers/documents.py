"""Document upload and list endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_db_gen
from app.models import DocumentListItem, DocumentMetadata
from app.db.repositories import get_document, list_documents
from app.services.ingestion_service import ingest_document
from app.utils.file_utils import ensure_dir, save_upload_file
from app.utils.validators import validate_upload_filename

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
def upload_document(file: UploadFile = File(...)):
    """Upload a document (PDF or .txt); extract text, chunk, and store."""
    if not file.filename or not validate_upload_filename(file.filename):
        raise HTTPException(400, "Only PDF and TXT files are allowed")
    s = get_settings()
    ensure_dir(s.upload_dir)
    ensure_dir(s.data_dir)
    content = file.file.read()
    max_bytes = s.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File too large (max {s.max_upload_mb} MB)")
    file_path, safe_name = save_upload_file(content, s.upload_dir, file.filename)
    logger.info("Saved %s (%d bytes), ingesting…", safe_name, len(content))
    # Open a session manually so we can control its lifecycle
    from app.db.session import get_session_factory
    factory = get_session_factory(s.database_url)
    db = factory()
    try:
        doc = ingest_document(db, file_path, safe_name, title=file.filename)
        result = {
            "document_id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "page_count": doc.page_count,
            "upload_timestamp": doc.upload_timestamp.isoformat(),
        }
        logger.info("Ingested doc %s (%s chunks)", doc.id, doc.page_count)
        return result
    finally:
        db.close()


@router.get("")
def list_docs(db: Session = Depends(get_db_gen)):
    """List all documents."""
    docs = list_documents(db)
    return [
        DocumentListItem(
            document_id=d.id,
            title=d.title,
            filename=d.filename,
            page_count=d.page_count,
            upload_timestamp=d.upload_timestamp,
        )
        for d in docs
    ]


@router.get("/{document_id}")
def get_doc(document_id: str, db: Session = Depends(get_db_gen)):
    """Get document metadata."""
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentMetadata(
        document_id=doc.id,
        title=doc.title,
        filename=doc.filename,
        page_count=doc.page_count,
        upload_timestamp=doc.upload_timestamp,
        file_size_bytes=doc.file_size_bytes,
    )
