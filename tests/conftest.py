import pytest

import routes


@pytest.fixture(autouse=True)
def no_real_database(monkeypatch):
    """API tests must never touch a real database (even if DATABASE_URL is in .env)."""
    saved = []
    monkeypatch.setattr(routes, "save_qa", lambda q, a: saved.append((q, a)))
    monkeypatch.setattr(routes, "get_history", lambda limit: [])
    return saved
