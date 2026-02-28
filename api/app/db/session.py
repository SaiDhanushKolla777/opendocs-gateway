"""Database session and engine (SQLite for v1)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db import models  # noqa: F401 - register models with Base

# Engine created lazily from config
_engine = None
_SessionLocal = None


def get_engine(database_url: str):
    """Create or return SQLite engine."""
    global _engine
    if _engine is None:
        if "sqlite" in database_url:
            from pathlib import Path
            path = database_url.replace("sqlite:///", "")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session_factory(database_url: str):
    """Return session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db(database_url: str):
    """Dependency that yields a DB session."""
    SessionLocal = get_session_factory(database_url)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
