"""Response models for API endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .citation import Citation


class AskResponse(BaseModel):
    """Response for single-document ask."""

    answer: str
    citations: List[Citation] = Field(default_factory=list)
    confidence_signal: Optional[str] = None
    insufficient_evidence: bool = False


class AskMultiResponse(BaseModel):
    """Response for multi-document ask."""

    answer: str
    citations: List[Citation] = Field(default_factory=list)
    insufficient_evidence: bool = False


class ExtractResponse(BaseModel):
    """Response for structured extraction."""

    data: dict
    citations: List[Citation] = Field(default_factory=list)
    validation_status: str = "valid"


class CompareResponse(BaseModel):
    """Response for document comparison."""

    summary: str
    structured_changes: dict
    citations_old: List[Citation] = Field(default_factory=list)
    citations_new: List[Citation] = Field(default_factory=list)
