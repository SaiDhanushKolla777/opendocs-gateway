"""Ingestion: PDF and text extraction, chunking, storage."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.repositories import create_chunks_batch, create_document, get_chunks_by_document
from app.services.embedding_service import embed_document_chunks
from app.db.models import DocumentModel
from app.models import Chunk
from app.utils.file_utils import unique_chunk_id, unique_document_id

try:
    import pypdf
except ImportError:
    pypdf = None  # type: ignore


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    """Extract text and page count from PDF. Returns (full_text, page_count)."""
    if pypdf is None:
        raise RuntimeError("pypdf is required for PDF extraction. Install with: pip install pypdf")
    reader = pypdf.PdfReader(file_path)
    page_count = len(reader.pages)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts), page_count


def extract_text_from_txt(file_path: str) -> Tuple[str, None]:
    """Read plain text file. Returns (text, None) — no page count for .txt."""
    return Path(file_path).read_text(encoding="utf-8", errors="replace"), None


def extract_text(file_path: str) -> Tuple[str, Optional[int]]:
    """Dispatch to PDF or plain-text extractor based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in {".txt", ".text", ".md"}:
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
    page_boundaries: Optional[List[Tuple[int, int]]] = None,
) -> List[Tuple[str, Optional[int]]]:
    """
    Split text into chunks. Returns list of (chunk_text, page_number).
    page_boundaries: optional list of (char_start, char_end) per page.
    """
    if not text.strip():
        return []
    chunks: List[Tuple[str, Optional[int]]] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # try to break at paragraph, line, or sentence boundary
            best = -1
            for sep in ["\n\n", "\n", ". "]:
                idx = text.rfind(sep, start + chunk_size // 2, end + 1)
                if idx > start:
                    best = idx + len(sep)
                    break
            if best > start:
                end = best
        snippet = text[start:end].strip()
        if snippet:
            chunks.append((snippet, None))
        # always advance by at least (end - overlap) but never backwards
        next_start = max(start + 1, end - overlap)
        start = next_start
    return chunks


def ingest_document(
    db: Session,
    file_path: str,
    filename: str,
    document_id: Optional[str] = None,
    title: Optional[str] = None,
) -> DocumentModel:
    """Extract text (PDF or .txt), chunk, store document and chunks."""
    full_text, page_count = extract_text(file_path)
    doc_id = document_id or unique_document_id()
    doc_title = title or Path(filename).stem

    doc = create_document(
        db=db,
        document_id=doc_id,
        title=doc_title,
        filename=filename,
        file_path=file_path,
        page_count=page_count,
        file_size_bytes=Path(file_path).stat().st_size,
    )

    raw_chunks = chunk_text(full_text)
    batch = [
        {
            "chunk_id": unique_chunk_id(),
            "document_id": doc_id,
            "document_title": doc_title,
            "text": text,
            "page_number": page_num,
            "chunk_index": i,
            "source_filename": filename,
        }
        for i, (text, page_num) in enumerate(raw_chunks)
    ]
    create_chunks_batch(db, batch)
    embed_document_chunks(db, doc_id)
    return doc


def document_to_chunks(db: Session, document_id: str) -> List[Chunk]:
    """Load document chunks as domain Chunk models."""
    rows = get_chunks_by_document(db, document_id)
    return [
        Chunk(
            chunk_id=r.id,
            document_id=r.document_id,
            document_title=r.document_title,
            text=r.text,
            page_number=r.page_number,
            chunk_index=r.chunk_index,
            char_length=r.char_length,
            source_filename=r.source_filename,
            upload_timestamp=r.upload_timestamp,
            embedding=r.embedding,
        )
        for r in rows
    ]
