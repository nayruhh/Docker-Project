"""The Redis flow from the assignment: HIT / MISS, ordering, and Redis failures."""

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services import cache


@pytest.fixture
def flow(monkeypatch):
    """Fake cache, model and database that record every call in order."""
    events, store = [], {}

    def get(q):
        events.append("redis_get")
        return store.get(q)

    def set_(q, a):
        events.append("redis_set")
        store[q] = a

    def model(q):
        events.append("generate")
        return f"answer to {q}"

    def save(q, a, cache_hit=False):
        events.append(f"save(cache_hit={cache_hit})")

    monkeypatch.setattr(routes, "get_cached", get)
    monkeypatch.setattr(routes, "set_cached", set_)
    monkeypatch.setattr(routes, "ask_model", model)
    monkeypatch.setattr(routes, "save_qa", save)
    return TestClient(app), events


def test_miss_checks_redis_generates_saves_then_caches(flow):
    client, events = flow
    r = client.post("/ask", json={"question": "hello"})
    assert r.headers["X-Cache"] == "MISS"
    assert events == ["redis_get", "generate", "save(cache_hit=False)", "redis_set"]


def test_hit_skips_generation_but_still_saves_a_history_row(flow):
    client, events = flow
    client.post("/ask", json={"question": "hello"})
    events.clear()
    r = client.post("/ask", json={"question": "hello"})
    assert r.headers["X-Cache"] == "HIT"
    assert r.json() == {"answer": "answer to hello"}
    assert events == ["redis_get", "save(cache_hit=True)"]  # no "generate"


def test_failed_generation_is_neither_saved_nor_cached(flow, monkeypatch):
    from fastapi import HTTPException

    client, events = flow

    def boom(q):
        raise HTTPException(status_code=504, detail="slow")

    monkeypatch.setattr(routes, "ask_model", boom)
    assert client.post("/ask", json={"question": "x"}).status_code == 504
    assert events == ["redis_get"]


def test_api_still_works_when_redis_is_down(monkeypatch):
    """Real cache module pointed at a dead Redis: the API must answer and still save."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")
    monkeypatch.setattr(cache, "_client", None)
    saved = []
    monkeypatch.setattr(routes, "get_cached", cache.get_cached)
    monkeypatch.setattr(routes, "set_cached", cache.set_cached)
    monkeypatch.setattr(routes, "ask_model", lambda q: "generated")
    monkeypatch.setattr(
        routes, "save_qa", lambda q, a, cache_hit=False: saved.append((q, a, cache_hit))
    )

    r = TestClient(app).post("/ask", json={"question": "hello"})
    assert r.status_code == 200
    assert r.json() == {"answer": "generated"}
    assert r.headers["X-Cache"] == "MISS"
    assert saved == [("hello", "generated", False)]
