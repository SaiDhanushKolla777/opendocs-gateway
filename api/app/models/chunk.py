"""Chunk models for retrieval."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""

    chunk_id: str
    document_id: str
    document_title: str
    page_number: Optional[int] = None
    chunk_index: int
    char_length: int
    source_filename: str
    upload_timestamp: Optional[datetime] = None


class Chunk(BaseModel):
    """A retrievable text chunk with metadata."""

    chunk_id: str
    document_id: str
    document_title: str
    text: str
    page_number: Optional[int] = None
    chunk_index: int
    char_length: int
    source_filename: str
    upload_timestamp: Optional[datetime] = None
