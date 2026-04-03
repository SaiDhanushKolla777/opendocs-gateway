"""Database session and engine (SQLite for v1)."""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db import models  # noqa: F401 - register models with Base

# Engine created lazily from config
_engine = None
_SessionLocal = None


def _migrate_sqlite_chunks_embedding(engine) -> None:
    """Add embedding column to existing SQLite DBs if missing."""
    if "sqlite" not in str(engine.url):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(chunks)")).fetchall()
        col_names = {row[1] for row in rows}
        if "embedding" not in col_names:
            conn.execute(text("ALTER TABLE chunks ADD COLUMN embedding BLOB"))
            conn.commit()


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
        _migrate_sqlite_chunks_embedding(_engine)
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
