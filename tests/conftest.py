import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    """App backed by a throwaway SQLite file. No Ollama, no network."""
    settings = Settings(model="gemma3:1b", ollama_url="http://localhost:11434",
                        db_path=tmp_path / "test.db", host="127.0.0.1", port=8000,
                        top_k=4, timeout=5.0)
    with TestClient(create_app(settings)) as c:
        yield c


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.reply = "Rosa grew tomatoes behind the house [1]."
        self.error = None

    def __call__(self, messages, model, base_url, **kwargs):
        self.calls.append({"messages": messages, "model": model, "kwargs": kwargs})
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr("app.llm.chat", fake)
    return fake


@pytest.fixture
def mock_http():
    def make(handler):
        return httpx.Client(transport=httpx.MockTransport(handler))
    return make


def add(client, title="Tomatoes", subject="Rosa", text="Rosa grew tomatoes behind the house.", **extra):
    resp = client.post("/api/memories", json={"title": title, "subject": subject, "text": text, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()
