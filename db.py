"""PostgreSQL storage for questions and answers.

Storage is optional: if DATABASE_URL is not set, or the database is down, the API
still answers questions and just logs the problem.
"""

import logging
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()
logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS questions (
    id         SERIAL PRIMARY KEY,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url, connect_timeout=5, row_factory=dict_row)


def init_db() -> None:
    """Create the table if needed. Logs (does not raise) if the database is unavailable."""
    try:
        with _connect() as conn:
            conn.execute(CREATE_TABLE)
        logger.info("Database ready")
    except Exception as e:
        logger.error("Database unavailable, answers will not be stored: %s", e)


def save_qa(question: str, answer: str) -> None:
    """Store one question/answer pair. Never raises, so a DB problem can't break /ask."""
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO questions (question, answer) VALUES (%s, %s)",
                (question, answer),
            )
        logger.info("Saved question/answer to database")
    except Exception as e:
        logger.error("Could not save to database: %s", e)


def get_history(limit: int = 20) -> list[dict]:
    """Return the most recent questions, newest first. Raises if the DB is unavailable."""
    with _connect() as conn:
        return conn.execute(
            "SELECT id, question, answer, created_at FROM questions "
            "ORDER BY id DESC LIMIT %s",
            (limit,),
        ).fetchall()
