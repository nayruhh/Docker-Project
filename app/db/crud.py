"""Reading and writing Q&A records."""

import logging

from sqlalchemy import select

from app.core.text import normalize_question
from app.db.models import QARecord
from app.db.session import session_scope

logger = logging.getLogger(__name__)


def save_qa(question: str, answer: str, cache_hit: bool = False) -> None:
    """Store one submission. Never raises, so a database problem can't break /ask."""
    try:
        with session_scope() as session:
            session.add(
                QARecord(
                    question=question,
                    normalized_question=normalize_question(question),
                    answer=answer,
                    cache_hit=cache_hit,
                )
            )
        logger.info("Saved question/answer to database (cache_hit=%s)", cache_hit)
    except Exception as e:
        logger.error("Could not save to database: %s", e)


def get_history(limit: int = 20) -> list[dict]:
    """Return the most recent submissions, newest first. Raises if the DB is unavailable."""
    with session_scope() as session:
        rows = session.scalars(
            select(QARecord).order_by(QARecord.created_at.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "cache_hit": r.cache_hit,
                "created_at": r.created_at,
            }
            for r in rows
        ]
