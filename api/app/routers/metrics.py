"""Metrics and benchmark endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.metrics_service import get_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics():
    """Current metrics snapshot (single-GPU observability)."""
    return get_metrics()


@router.get("/benchmarks/summary")
def benchmarks_summary():
    """Benchmark summary (alias for metrics)."""
    return get_metrics()
