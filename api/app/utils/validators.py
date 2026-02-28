"""Validation utilities."""
from __future__ import annotations

import re
from typing import Optional


def safe_filename(name: str) -> str:
    """Return a safe filename (strip path components)."""
    return re.sub(r"[^\w\s\-\.]", "", name).strip() or "document"


ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def validate_upload_filename(filename: str) -> bool:
    """Check that filename has an allowed extension (.pdf or .txt)."""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


def get_file_extension(filename: str) -> str:
    """Return lowercase extension including the dot."""
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
