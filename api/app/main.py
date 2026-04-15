"""OpenDocs Gateway — FastAPI application (single-GPU MI300X)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging
from app.routers import (
    health_router,
    documents_router,
    ask_router,
    extract_router,
    compare_router,
    reports_router,
    metrics_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    ensure_dirs(s)
    yield
    # shutdown if needed


def ensure_dirs(s):
    from pathlib import Path
    Path(s.data_dir).mkdir(parents=True, exist_ok=True)
    Path(s.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(s.faiss_index_dir).mkdir(parents=True, exist_ok=True)
    if "sqlite" in s.database_url:
        db_path = s.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    s = get_settings()
    setup_logging(s.log_level)
    app = FastAPI(
        title="OpenDocs Gateway",
        description="Long-context document intelligence (single AMD MI300X GPU)",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(ask_router)
    app.include_router(extract_router)
    app.include_router(compare_router)
    app.include_router(reports_router)
    app.include_router(metrics_router)
    return app


app = create_app()
