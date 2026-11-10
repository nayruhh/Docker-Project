import os

import pytest
import redis
from fastapi.testclient import TestClient

import cache
import routes
from main import app


# ---- API behaviour (cache faked with a dict) -------------------------------
@pytest.fixture
def api(monkeypatch):
    store, calls = {}, []

    def fake_model(q):
        calls.append(q)
        return f"answer to {q}"

    monkeypatch.setattr(routes, "ask_model", fake_model)
    monkeypatch.setattr(routes, "get_cached", lambda q: store.get(q))
    monkeypatch.setattr(routes, "set_cached", lambda q, a: store.__setitem__(q, a))
    return TestClient(app), calls


def test_first_request_is_a_miss_second_is_a_hit(api):
    client, calls = api
    first = client.post("/ask", json={"question": "hello"})
    second = client.post("/ask", json={"question": "hello"})
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert first.json() == second.json() == {"answer": "answer to hello"}
    assert calls == ["hello"]  # the model was only called once


def test_different_questions_are_not_shared(api):
    client, calls = api
    client.post("/ask", json={"question": "a"})
    r = client.post("/ask", json={"question": "b"})
    assert r.headers["X-Cache"] == "MISS"
    assert calls == ["a", "b"]


def test_cache_hit_is_still_saved_to_history(api, no_real_database):
    client, _ = api
    client.post("/ask", json={"question": "x"})
    client.post("/ask", json={"question": "x"})
    assert len(no_real_database) == 2


# ---- cache module ----------------------------------------------------------
def test_key_ignores_case_and_extra_spaces():
    assert cache._key("Hello   World") == cache._key("hello world")
    assert cache._key("hello") != cache._key("goodbye")


def test_disabled_without_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(cache, "_client", None)
    assert cache.get_cached("q") is None
    cache.set_cached("q", "a")  # must not raise


def test_redis_down_does_not_raise(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")
    monkeypatch.setattr(cache, "_client", None)
    assert cache.get_cached("q") is None
    cache.set_cached("q", "a")  # must not raise


# ---- real Redis (skipped unless TEST_REDIS_URL is set) ---------------------
TEST_URL = os.getenv("TEST_REDIS_URL")


@pytest.mark.skipif(not TEST_URL, reason="TEST_REDIS_URL not set")
def test_round_trip_and_ttl_with_real_redis(monkeypatch):
    monkeypatch.setenv("REDIS_URL", TEST_URL)
    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache, "CACHE_TTL_SECONDS", 60)
    redis.Redis.from_url(TEST_URL).flushdb()
    assert cache.get_cached("capital of france?") is None
    cache.set_cached("capital of france?", "Paris")
    assert cache.get_cached("Capital  of France?") == "Paris"
    ttl = redis.Redis.from_url(TEST_URL).ttl(cache._key("capital of france?"))
    assert 0 < ttl <= 60
