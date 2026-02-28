"""File handling utilities."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from app.utils.validators import safe_filename


def ensure_dir(path: str | Path) -> Path:
    """Create directory if it does not exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def unique_document_id() -> str:
    """Generate a unique document id."""
    return str(uuid.uuid4())[:16].replace("-", "")


def unique_chunk_id() -> str:
    """Generate a unique chunk id."""
    return str(uuid.uuid4())[:16].replace("-", "")


def save_upload_file(content: bytes, upload_dir: str, filename: str) -> tuple[str, str]:
    """Save uploaded file; return (absolute_path, safe_filename)."""
    ensure_dir(upload_dir)
    safe = safe_filename(filename) or "document"
    doc_id = unique_document_id()
    subdir = Path(upload_dir) / doc_id
    ensure_dir(subdir)
    path = subdir / safe
    path.write_bytes(content)
    return str(path), safe
