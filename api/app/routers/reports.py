"""Report export endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.services.report_service import get_report, export_report_json

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}")
def get_report_by_id(report_id: str):
    """Get report by id (JSON)."""
    r = get_report(report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    return r


@router.get("/reports/{report_id}/export", response_class=PlainTextResponse)
def export_report(report_id: str):
    """Export report as JSON text."""
    data = export_report_json(report_id)
    if not data:
        raise HTTPException(404, "Report not found")
    return data
