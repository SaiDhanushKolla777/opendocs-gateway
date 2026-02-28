"""Repository layer for documents and chunks."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import ChunkModel, DocumentModel


def create_document(
    db: Session,
    document_id: str,
    title: str,
    filename: str,
    file_path: str,
    page_count: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
) -> DocumentModel:
    """Persist document metadata."""
    doc = DocumentModel(
        id=document_id,
        title=title,
        filename=filename,
        file_path=file_path,
        page_count=page_count,
        file_size_bytes=file_size_bytes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, document_id: str) -> Optional[DocumentModel]:
    """Get document by id."""
    return db.query(DocumentModel).filter(DocumentModel.id == document_id).first()


def list_documents(db: Session) -> List[DocumentModel]:
    """List all documents."""
    return db.query(DocumentModel).order_by(DocumentModel.upload_timestamp.desc()).all()


def create_chunk(
    db: Session,
    chunk_id: str,
    document_id: str,
    document_title: str,
    text: str,
    page_number: Optional[int],
    chunk_index: int,
    source_filename: str,
) -> ChunkModel:
    """Persist a single chunk (commits immediately)."""
    c = ChunkModel(
        id=chunk_id,
        document_id=document_id,
        document_title=document_title,
        text=text,
        page_number=page_number,
        chunk_index=chunk_index,
        char_length=len(text),
        source_filename=source_filename,
        upload_timestamp=datetime.utcnow(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def create_chunks_batch(
    db: Session,
    chunks: List[dict],
) -> int:
    """Persist many chunks in one transaction. Returns count inserted."""
    objects = []
    now = datetime.utcnow()
    for ch in chunks:
        objects.append(ChunkModel(
            id=ch["chunk_id"],
            document_id=ch["document_id"],
            document_title=ch["document_title"],
            text=ch["text"],
            page_number=ch.get("page_number"),
            chunk_index=ch["chunk_index"],
            char_length=len(ch["text"]),
            source_filename=ch["source_filename"],
            upload_timestamp=now,
        ))
    db.add_all(objects)
    db.commit()
    return len(objects)


def get_chunks_by_document(db: Session, document_id: str) -> List[ChunkModel]:
    """Get all chunks for a document."""
    return (
        db.query(ChunkModel)
        .filter(ChunkModel.document_id == document_id)
        .order_by(ChunkModel.chunk_index)
        .all()
    )


def get_chunks_by_ids(db: Session, chunk_ids: List[str]) -> List[ChunkModel]:
    """Get chunks by ids."""
    if not chunk_ids:
        return []
    return db.query(ChunkModel).filter(ChunkModel.id.in_(chunk_ids)).all()
