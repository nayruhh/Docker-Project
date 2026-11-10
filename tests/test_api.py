"""API tests. The model call is mocked so tests are fast, free and deterministic."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import routes
from main import app
from schemas import MAX_QUESTION_LENGTH


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes, "ask_model", lambda q: f"echo: {q}")
    return TestClient(app)


# ---- valid requests -------------------------------------------------------
def test_valid_question_returns_answer(client):
    r = client.post("/ask", json={"question": "What is the capital of France?"})
    assert r.status_code == 200
    assert r.json() == {"answer": "echo: What is the capital of France?"}


def test_question_is_trimmed(client):
    r = client.post("/ask", json={"question": "  hi  "})
    assert r.status_code == 200
    assert r.json()["answer"] == "echo: hi"


def test_question_at_max_length_is_accepted(client):
    r = client.post("/ask", json={"question": "a" * MAX_QUESTION_LENGTH})
    assert r.status_code == 200


# ---- invalid requests -----------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "   "},
        {"question": "a" * (MAX_QUESTION_LENGTH + 1)},
        {},
        {"question": 123},
        {"question": None},
        {"question": "hi", "extra": 1},
    ],
    ids=["empty", "blank", "too-long", "missing", "wrong-type", "null", "extra-field"],
)
def test_invalid_request_returns_422(client, body):
    r = client.post("/ask", json=body)
    assert r.status_code == 422
    assert "detail" in r.json()


def test_invalid_json_returns_422(client):
    r = client.post("/ask", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_wrong_method_returns_405(client):
    assert client.get("/ask").status_code == 405


# ---- model/provider errors are mapped to clean HTTP errors ----------------
@pytest.mark.parametrize("status", [429, 502, 504])
def test_model_errors_are_passed_through(monkeypatch, status):
    def boom(_):
        raise HTTPException(status_code=status, detail="model problem")

    monkeypatch.setattr(routes, "ask_model", boom)
    r = TestClient(app).post("/ask", json={"question": "hi"})
    assert r.status_code == status
    assert r.json() == {"detail": "model problem"}
