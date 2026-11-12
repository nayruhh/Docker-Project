"""Runs against a real PostgreSQL. Skipped unless TEST_DATABASE_URL is set.

Example: TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/db uv run pytest
It also proves the Alembic migrations build the schema from scratch.

WARNING: every test drops and recreates the tables. Only point TEST_DATABASE_URL at a
throwaway database, never at one holding data you care about.
"""

import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.db import crud, session

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture(autouse=True)
def fresh_migrated_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    session.reset_engine()
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield
    session.reset_engine()


def test_migration_creates_expected_schema():
    insp = inspect(session.get_engine())
    cols = {c["name"]: c for c in insp.get_columns("qa_records")}
    assert set(cols) == {
        "id",
        "question",
        "normalized_question",
        "answer",
        "cache_hit",
        "created_at",
    }
    assert not cols["question"]["nullable"] and not cols["answer"]["nullable"]
    indexes = {tuple(i["column_names"]) for i in insp.get_indexes("qa_records")}
    assert ("created_at",) in indexes
    assert insp.get_pk_constraint("qa_records")["constrained_columns"] == ["id"]


def test_save_stores_original_and_normalized_question():
    crud.save_qa("What is  the Capital of France?", "Paris")
    (row,) = crud.get_history(10)
    assert row["question"] == "What is  the Capital of France?"  # original kept as submitted
    assert isinstance(row["id"], uuid.UUID)
    assert row["cache_hit"] is False
    with session.get_engine().connect() as conn:
        norm = conn.execute(text("select normalized_question from qa_records")).scalar_one()
    assert norm == "what is the capital of france?"


def test_history_is_newest_first_and_limited():
    for i in range(3):
        crud.save_qa(f"q{i}", "a")
    assert [r["question"] for r in crud.get_history(10)] == ["q2", "q1", "q0"]
    assert len(crud.get_history(2)) == 2


def test_same_question_twice_creates_two_rows_and_records_cache_hit():
    crud.save_qa("same?", "one", cache_hit=False)
    crud.save_qa("same?", "one", cache_hit=True)
    rows = crud.get_history(10)
    assert len(rows) == 2
    assert [r["cache_hit"] for r in rows] == [True, False]
    assert rows[0]["id"] != rows[1]["id"]


def test_save_never_raises_when_db_is_down(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@localhost:1/none")
    session.reset_engine()
    crud.save_qa("q", "a")  # must not raise
