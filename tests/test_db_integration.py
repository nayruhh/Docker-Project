"""Runs against a real PostgreSQL. Skipped unless TEST_DATABASE_URL is set.

Example: TEST_DATABASE_URL=postgresql://user:pass@localhost:55432/db uv run pytest
"""

import os

import pytest

import db

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    db.init_db()
    with db._connect() as conn:
        conn.execute("TRUNCATE questions")


def test_save_and_read_back_newest_first():
    db.save_qa("first?", "one")
    db.save_qa("second?", "two")
    rows = db.get_history(10)
    assert [r["question"] for r in rows] == ["second?", "first?"]
    assert rows[0]["answer"] == "two"
    assert rows[0]["created_at"] is not None


def test_limit_is_respected():
    for i in range(3):
        db.save_qa(f"q{i}", "a")
    assert len(db.get_history(2)) == 2


def test_save_never_raises_when_db_is_down(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@localhost:1/none")
    db.save_qa("q", "a")  # must not raise
