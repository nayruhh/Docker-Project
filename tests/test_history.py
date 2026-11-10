from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import routes
from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes, "ask_model", lambda q: f"echo: {q}")
    return TestClient(app)


def test_ask_saves_question_and_answer(client, no_real_database):
    r = client.post("/ask", json={"question": "  hi  "})
    assert r.status_code == 200
    assert no_real_database == [("hi", "echo: hi")]


def test_failed_ask_is_not_saved(monkeypatch, no_real_database):
    from fastapi import HTTPException

    def boom(_):
        raise HTTPException(status_code=504, detail="slow")

    monkeypatch.setattr(routes, "ask_model", boom)
    assert TestClient(app).post("/ask", json={"question": "hi"}).status_code == 504
    assert no_real_database == []


def test_history_returns_rows(monkeypatch, client):
    row = {
        "id": 1,
        "question": "q",
        "answer": "a",
        "created_at": datetime(2026, 11, 10, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(routes, "get_history", lambda limit: [row][:limit])
    r = client.get("/history")
    assert r.status_code == 200
    assert r.json()[0]["question"] == "q"


@pytest.mark.parametrize("limit", ["0", "101", "abc"])
def test_history_rejects_bad_limit(client, limit):
    assert client.get("/history", params={"limit": limit}).status_code == 422


def test_history_returns_503_when_db_down(monkeypatch, client):
    def down(limit):
        raise RuntimeError("no db")

    monkeypatch.setattr(routes, "get_history", down)
    r = client.get("/history")
    assert r.status_code == 503
    assert r.json() == {"detail": "Database unavailable."}
