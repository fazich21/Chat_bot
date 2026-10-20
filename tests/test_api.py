"""Tests for the FastAPI endpoints (offline, with fakes)."""
import json

import pytest
from fastapi.testclient import TestClient

import api
from conftest import FakeLLM
from src.chatbot import Chatbot


@pytest.fixture
def client(retriever):
    api.state["bot"] = Chatbot(retriever=retriever, llm_client=FakeLLM("I work at Business Analytics."))
    with TestClient(api.app) as c:
        yield c


def read_events(response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["chunks"] > 0


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["name"] == "M Faizan" and body["suggestions"]


def test_chat_streams_events(client):
    r = client.post("/api/chat", json={"message": "Where do you work?", "history": []})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = read_events(r)
    assert events[0]["type"] == "sources" and events[-1]["type"] == "done"
    assert "Business Analytics" in "".join(e.get("text", "") for e in events)


def test_chat_rate_limit(client):
    for _ in range(10):
        client.post("/api/chat", json={"message": "hi"})
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 429


def test_chat_rejects_huge_message(client):
    assert client.post("/api/chat", json={"message": "x" * 5000}).status_code == 422
