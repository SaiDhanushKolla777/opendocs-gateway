"""Report generation and export."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.models import Citation


# In-memory store for v1; can persist to DB or file later
_reports: Dict[str, Dict[str, Any]] = {}


def create_report(
    document_id: str,
    document_title: str,
    summary: Optional[str] = None,
    extracted_data: Optional[Dict] = None,
    citations: Optional[List[Citation]] = None,
    change_summary: Optional[str] = None,
) -> str:
    """Create a report and return report_id."""
    report_id = str(uuid.uuid4())[:12]
    _reports[report_id] = {
        "report_id": report_id,
        "document_id": document_id,
        "document_title": document_title,
        "summary": summary or "",
        "extracted_data": extracted_data or {},
        "citations": [c.model_dump() for c in (citations or [])],
        "change_summary": change_summary,
        "created_at": datetime.utcnow().isoformat(),
    }
    return report_id


def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Get report by id."""
    return _reports.get(report_id)


def export_report_json(report_id: str) -> Optional[str]:
    """Export report as JSON string."""
    r = get_report(report_id)
    if not r:
        return None
    return json.dumps(r, indent=2)
