"""API routers."""
from .health import router as health_router
from .documents import router as documents_router
from .ask import router as ask_router
from .extract import router as extract_router
from .compare import router as compare_router
from .reports import router as reports_router
from .metrics import router as metrics_router

__all__ = [
    "health_router",
    "documents_router",
    "ask_router",
    "extract_router",
    "compare_router",
    "reports_router",
    "metrics_router",
]
