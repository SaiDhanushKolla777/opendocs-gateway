"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness/readiness."""
    return {"status": "ok", "service": "opendocs-gateway"}


@router.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Minimal upload test — just return file info."""
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}
