from app.database import Database


def test_database_roundtrip_and_delete_all(tmp_path):
    path = tmp_path / "data" / "x.db"
    db = Database(path)
    assert path.exists() and db.count_memories() == 0
    db.add_memory("T", "Rosa", "tomatoes")
    db.add_ofrenda("Rosa", "r", ["a"], "c", "gemma3:1b", [1])
    db.set_setting("model", "qwen3:0.6b")
    assert db.get_setting("model") == "qwen3:0.6b"
    assert db.delete_all() == {"memories": 1, "ofrendas": 1}
    assert db.count_memories() == 0 and db.list_ofrendas() == []
    assert db.search_fts('"tomatoes"', 5) == []
    assert db.add_memory("T2", "Rosa", "x")["id"] == 1  # ids restart
    db.close()
