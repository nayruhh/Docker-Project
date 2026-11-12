"""Engine and session handling."""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_database_url

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create the engine on first use. Raises RuntimeError if no database is configured."""
    global _engine, _session_factory
    if _engine is None:
        url = get_database_url()
        if not url:
            raise RuntimeError("No database configured (set DATABASE_URL or POSTGRES_HOST)")
        _engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        _session_factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Drop the cached engine (used by tests that change the database URL)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


@contextmanager
def session_scope():
    """Yield a session that commits on success and rolls back on error."""
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database() -> bool:
    """Log whether the database is reachable. Never raises."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database ready")
        return True
    except Exception as e:
        logger.error("Database unavailable, answers will not be stored: %s", e)
        return False
