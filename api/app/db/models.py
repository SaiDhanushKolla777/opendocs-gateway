"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class DocumentModel(Base):
    """Stored document metadata."""

    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    page_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)


class ChunkModel(Base):
    """Stored text chunk for retrieval."""

    __tablename__ = "chunks"

    id = Column(String(64), primary_key=True, index=True)
    document_id = Column(String(64), nullable=False, index=True)
    document_title = Column(String(512), nullable=False)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    char_length = Column(Integer, nullable=False)
    source_filename = Column(String(512), nullable=False)
    upload_timestamp = Column(DateTime, nullable=True)
