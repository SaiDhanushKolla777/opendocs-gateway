"""Document domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""

    document_id: str
    title: str
    filename: str
    page_count: Optional[int] = None
    upload_timestamp: datetime
    file_size_bytes: Optional[int] = None


class DocumentCreate(BaseModel):
    """Input for creating/uploading a document."""

    title: Optional[str] = None
    filename: str


class DocumentListItem(BaseModel):
    """Document summary for list views."""

    document_id: str
    title: str
    filename: str
    page_count: Optional[int] = None
    upload_timestamp: datetime
