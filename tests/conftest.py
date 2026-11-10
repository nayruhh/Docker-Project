import pytest

import routes


@pytest.fixture(autouse=True)
def no_real_database(monkeypatch):
    """API tests must never touch a real database or Redis (even if set in .env)."""
    saved = []
    monkeypatch.setattr(routes, "save_qa", lambda q, a: saved.append((q, a)))
    monkeypatch.setattr(routes, "get_history", lambda limit: [])
    monkeypatch.setattr(routes, "get_cached", lambda q: None)
    monkeypatch.setattr(routes, "set_cached", lambda q, a: None)
    return saved
