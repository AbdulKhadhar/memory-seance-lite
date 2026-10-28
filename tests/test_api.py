import json

from app import llm
from tests.conftest import add


def test_add_and_list_memory(client):
    m = add(client, tags=" garden , summer ,", date="2019-07-04")
    assert m["tags"] == "garden, summer"
    listed = client.get("/api/memories").json()
    assert [x["id"] for x in listed] == [m["id"]]


def test_edit_and_delete_memory(client):
    m = add(client)
    resp = client.put(f"/api/memories/{m['id']}", json={"title": "T", "subject": "Rosa", "text": "Edited."})
    assert resp.json()["text"] == "Edited."
    assert client.delete(f"/api/memories/{m['id']}").status_code == 200
    assert client.delete(f"/api/memories/{m['id']}").status_code == 404


def test_invalid_input_rejected(client):
    bad = [
        {"title": "", "subject": "Rosa", "text": "x"},
        {"title": "t", "subject": "   ", "text": "x"},
        {"title": "t", "subject": "Rosa", "text": "x", "date": "yesterday"},
        {"title": "t", "subject": "Rosa", "text": "x" * 2001},
    ]
    for body in bad:
        assert client.post("/api/memories", json=body).status_code == 422


def test_seance_empty_database_does_not_call_model(client, fake_llm):
    body = client.post("/api/seance", json={"question": "What did she cook?"}).json()
    assert body["answered"] is False and body["reason"] == "empty"
    assert fake_llm.calls == []


def test_seance_rejects_when_no_relevant_memory(client, fake_llm):
    add(client)
    body = client.post("/api/seance", json={"question": "What is the capital of France?"}).json()
    assert body["answered"] is False and body["sources"] == []
    assert "can't answer" in body["answer"]
    assert fake_llm.calls == []


def test_seance_answers_with_sources(client, fake_llm):
    m = add(client)
    add(client, title="Radio", text="He always hummed along to the radio.", subject="Beto")
    body = client.post("/api/seance", json={"question": "Did Rosa grow tomatoes?"}).json()
    assert body["answered"] is True
    assert [s["id"] for s in body["sources"]] == [m["id"]]
    assert "Rosa grew tomatoes" in fake_llm.calls[0]["messages"][1]["content"]
    assert "not communication with a deceased person" in body["disclaimer"]


def test_seance_model_can_decline(client, fake_llm):
    add(client)
    fake_llm.reply = "NO_ANSWER"
    body = client.post("/api/seance", json={"question": "Where did Rosa grow tomatoes?"}).json()
    assert body["answered"] is False and body["reason"] == "model_declined"


def test_ofrenda_generated_and_saved(client, fake_llm):
    for i in range(7):
        add(client, title=f"Memory {i}", text=f"Rosa did thing number {i}.")
    fake_llm.reply = json.dumps({"remembrance": "Rosa is remembered.", "remembered": ["a", "b", "c"],
                                 "closing": "Until the candles meet again."})
    resp = client.post("/api/ofrenda", json={"subject": "rosa"})
    assert resp.status_code == 201
    assert len(resp.json()["source_ids"]) == 4  # capped by top_k
    assert len(client.get("/api/ofrendas").json()) == 1


def test_ofrenda_no_memories(client, fake_llm):
    resp = client.post("/api/ofrenda", json={"subject": "Nobody"})
    assert resp.status_code == 404 and resp.json()["detail"]["code"] == "no_memories"


def test_ofrenda_unusable_output_retries_then_fails(client, fake_llm):
    add(client)
    fake_llm.reply = "sorry, here is some prose instead of JSON"
    resp = client.post("/api/ofrenda", json={"subject": "Rosa"})
    assert resp.status_code == 502 and resp.json()["detail"]["code"] == "llm_bad_output"
    assert len(fake_llm.calls) == 2
    assert client.get("/api/ofrendas").json() == []


def test_ollama_down_and_model_missing_errors(client, fake_llm):
    add(client)
    fake_llm.error = llm.OllamaUnavailable("Cannot reach Ollama")
    resp = client.post("/api/seance", json={"question": "Rosa tomatoes?"})
    assert resp.status_code == 503 and resp.json()["detail"]["code"] == "ollama_unavailable"
    fake_llm.error = llm.ModelNotInstalled("Model 'x' is not installed. Run: ollama pull x")
    resp = client.post("/api/seance", json={"question": "Rosa tomatoes?"})
    assert resp.status_code == 409


def test_delete_all_requires_confirmation_and_wipes(client, fake_llm):
    add(client)
    fake_llm.reply = json.dumps({"remembrance": "r", "remembered": ["a"], "closing": "c"})
    client.post("/api/ofrenda", json={"subject": "Rosa"})
    assert client.delete("/api/data").status_code == 400
    assert client.get("/api/memories").json() != []
    resp = client.delete("/api/data?confirm=yes")
    assert resp.json()["deleted"] == {"memories": 1, "ofrendas": 1}
    assert client.get("/api/memories").json() == []
    assert client.get("/api/ofrendas").json() == []
    assert client.get("/api/subjects").json() == []


def test_settings_roundtrip_and_validation(client):
    resp = client.put("/api/settings", json={"model": "qwen3:0.6b", "ollama_url": "http://localhost:11434/"})
    assert resp.json()["model"] == "qwen3:0.6b" and resp.json()["ollama_url"] == "http://localhost:11434"
    assert client.put("/api/settings", json={"model": "bad model!", "ollama_url": "http://x.y"}).status_code == 422
    assert client.put("/api/settings", json={"model": "gemma3:1b", "ollama_url": "ftp://x.y"}).status_code == 422


def test_index_served_with_disclaimer(client):
    page = client.get("/")
    assert page.status_code == 200 and "not communication with" in page.text.lower()
    assert "Content-Security-Policy" in page.headers
