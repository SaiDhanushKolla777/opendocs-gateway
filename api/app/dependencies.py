"""FastAPI dependencies."""
from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session_factory

_settings = None


def get_config():
    """Return app settings."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_db_gen() -> Generator[Session, None, None]:
    """Yield DB session."""
    s = get_config()
    factory = get_session_factory(s.database_url)
    db = factory()
    try:
        yield db
    finally:
        db.close()
