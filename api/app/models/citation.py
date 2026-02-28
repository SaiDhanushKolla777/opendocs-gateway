"""Citation models for grounded answers."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single citation to source evidence."""

    chunk_id: str
    document_id: str
    document_title: str
    snippet: str
    page_number: Optional[int] = None
