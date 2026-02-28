"""Request body models for API endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer_mode: str = Field(default="plain_english")
    max_citations: Optional[int] = None
    history: Optional[List[ChatMessage]] = None


class AskMultiRequest(BaseModel):
    document_ids: List[str] = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    answer_mode: str = Field(default="plain_english")
    history: Optional[List[ChatMessage]] = None


class ExtractRequest(BaseModel):
    extraction_type: str = Field(default="default")
    schema_request: Optional[dict] = None


class CompareRequest(BaseModel):
    old_document_id: str
    new_document_id: str
