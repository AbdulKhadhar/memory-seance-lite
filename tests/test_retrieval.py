from app import retrieval
from tests.conftest import add


def test_tokenize_drops_stopwords():
    assert retrieval.tokenize("What did Rosa cook for us?") == ["rosa", "cook"]


def _seed(client):
    add(client, title="Tomatoes", subject="Rosa", text="Rosa grew tomatoes behind the house.")
    add(client, title="Radio", subject="Beto", text="Beto hummed along to the radio every morning.")
    add(client, title="Lumen RSS", subject="Lumen", text="The feed parser was abandoned after version 0.3.", tags="project")


def test_fts_ranks_relevant_memory_first(client):
    _seed(client)
    db = client.app.state.db
    assert db.fts_enabled
    hits = retrieval.retrieve(db, "Who was growing tomato plants?", k=3)
    assert hits and hits[0]["title"] == "Tomatoes"
    assert all(h["subject"] != "Beto" for h in hits)


def test_subject_filter_and_limit(client):
    _seed(client)
    db = client.app.state.db
    assert retrieval.retrieve(db, "radio tomatoes parser", subject="Beto", k=5)[0]["subject"] == "Beto"
    assert len(retrieval.retrieve(db, "radio tomatoes parser", k=2)) == 2


def test_no_match_returns_empty(client):
    _seed(client)
    assert retrieval.retrieve(client.app.state.db, "quantum chromodynamics") == []
    assert retrieval.retrieve(client.app.state.db, "what is the") == []  # only stopwords


def test_python_fallback_when_fts_missing(client):
    _seed(client)
    db = client.app.state.db
    db.fts_enabled = False
    hits = retrieval.retrieve(db, "growing tomatoes", k=3)
    assert hits[0]["title"] == "Tomatoes"
    assert retrieval.retrieve(db, "quantum") == []


def test_search_follows_edits_and_deletes(client):
    m = add(client, text="Rosa grew tomatoes.")
    db = client.app.state.db
    client.put(f"/api/memories/{m['id']}", json={"title": "Peppers", "subject": "Rosa", "text": "Rosa grew peppers."})
    assert retrieval.retrieve(db, "tomatoes") == []
    assert retrieval.retrieve(db, "peppers")
    client.delete(f"/api/memories/{m['id']}")
    assert retrieval.retrieve(db, "peppers") == []
