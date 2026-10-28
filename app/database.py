"""SQLite storage. One file, standard library only. FTS5 is used when available."""
import json
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS ofrendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    remembrance TEXT NOT NULL,
    remembered TEXT NOT NULL,
    closing TEXT NOT NULL,
    model TEXT NOT NULL,
    source_ids TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title, subject, text, tags,
    content='memories', content_rowid='id',
    tokenize='porter unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, title, subject, text, tags)
    VALUES (new.id, new.title, new.subject, new.text, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, subject, text, tags)
    VALUES ('delete', old.id, old.title, old.subject, old.text, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, subject, text, tags)
    VALUES ('delete', old.id, old.title, old.subject, old.text, old.tags);
    INSERT INTO memories_fts(rowid, title, subject, text, tags)
    VALUES (new.id, new.title, new.subject, new.text, new.tags);
END;
"""


def _row(row):
    return dict(row) if row is not None else None


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.fts_enabled = False
        with self._lock:
            # Memory and disk optimization pragmas:
            # - WAL journal mode: concurrent reads without locking, efficient writes
            # - synchronous=NORMAL: safe in WAL mode while avoiding heavy disk flush stalls
            # - cache_size=-2000: limits in-memory page cache to ~2 MB
            # - temp_store=MEMORY: keeps temporary tables/sorts in memory without disk churn
            # - mmap_size=268435456: allows memory-mapped I/O up to 256MB if supported
            # - auto_vacuum=INCREMENTAL: enables automatic unused page reclamation
            try:
                self.conn.execute("PRAGMA journal_mode=WAL")
                self.conn.execute("PRAGMA synchronous=NORMAL")
                self.conn.execute("PRAGMA cache_size=-2000")
                self.conn.execute("PRAGMA temp_store=MEMORY")
                self.conn.execute("PRAGMA mmap_size=268435456")
            except sqlite3.OperationalError:
                pass
            self.conn.executescript(SCHEMA)
            try:
                self.conn.executescript(FTS_SCHEMA)
                self.fts_enabled = True
            except sqlite3.OperationalError:
                self.fts_enabled = False  # retrieval falls back to Python scoring
            self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- memories -------------------------------------------------------
    def add_memory(self, title, subject, text, tags="", date=""):
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO memories(title, subject, text, tags, date) VALUES (?,?,?,?,?)",
                (title, subject, text, tags, date),
            )
            self.conn.commit()
            return self._get(cur.lastrowid)

    def _get(self, memory_id):
        return _row(self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone())

    def get_memory(self, memory_id):
        with self._lock:
            return self._get(memory_id)

    def update_memory(self, memory_id, title, subject, text, tags="", date=""):
        with self._lock:
            cur = self.conn.execute(
                "UPDATE memories SET title=?, subject=?, text=?, tags=?, date=? WHERE id=?",
                (title, subject, text, tags, date, memory_id),
            )
            self.conn.commit()
            return self._get(memory_id) if cur.rowcount else None

    def delete_memory(self, memory_id):
        with self._lock:
            cur = self.conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            self.conn.commit()
            return cur.rowcount > 0

    def list_memories(self, subject=None, limit=None):
        sql, params = "SELECT * FROM memories", []
        if subject:
            sql += " WHERE subject = ? COLLATE NOCASE"
            params.append(subject)
        sql += " ORDER BY id DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock:
            return [dict(r) for r in self.conn.execute(sql, params)]

    def count_memories(self):
        with self._lock:
            return self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def subjects(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT MIN(subject) AS subject, COUNT(*) AS count FROM memories "
                "GROUP BY subject COLLATE NOCASE ORDER BY subject COLLATE NOCASE"
            )
            return [dict(r) for r in rows]

    def search_fts(self, match_query, limit, subject=None):
        """BM25-ranked search. Title and subject matches weigh more than body text."""
        sql = (
            "SELECT m.*, bm25(memories_fts, 4.0, 3.0, 1.0, 2.0) AS rank "
            "FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid "
            "WHERE memories_fts MATCH ?"
        )
        params = [match_query]
        if subject:
            sql += " AND m.subject = ? COLLATE NOCASE"
            params.append(subject)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = [dict(r) for r in self.conn.execute(sql, params)]
        for r in rows:
            r["score"] = round(-r.pop("rank"), 3)
        return rows

    # ---- ofrendas -------------------------------------------------------
    def add_ofrenda(self, subject, remembrance, remembered, closing, model, source_ids):
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO ofrendas(subject, remembrance, remembered, closing, model, source_ids)"
                " VALUES (?,?,?,?,?,?)",
                (subject, remembrance, json.dumps(remembered), closing, model, json.dumps(source_ids)),
            )
            self.conn.commit()
            row = self.conn.execute("SELECT * FROM ofrendas WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._decode_ofrenda(row)

    @staticmethod
    def _decode_ofrenda(row):
        d = dict(row)
        d["remembered"] = json.loads(d["remembered"])
        d["source_ids"] = json.loads(d["source_ids"])
        return d

    def list_ofrendas(self):
        with self._lock:
            rows = self.conn.execute("SELECT * FROM ofrendas ORDER BY id DESC").fetchall()
        return [self._decode_ofrenda(r) for r in rows]

    def delete_ofrenda(self, ofrenda_id):
        with self._lock:
            cur = self.conn.execute("DELETE FROM ofrendas WHERE id=?", (ofrenda_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---- settings -------------------------------------------------------
    def get_setting(self, key, default=None):
        with self._lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self._lock:
            self.conn.execute(
                "INSERT INTO settings(key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self.conn.commit()

    # ---- wipe -----------------------------------------------------------
    def delete_all(self):
        """Erase every memory and saved ofrenda, then compact the file."""
        with self._lock:
            n_mem = self.conn.execute("DELETE FROM memories").rowcount
            n_ofr = self.conn.execute("DELETE FROM ofrendas").rowcount
            self.conn.execute("DELETE FROM sqlite_sequence")
            self.conn.commit()
            if self.fts_enabled:
                self.conn.execute("INSERT INTO memories_fts(memories_fts) VALUES ('rebuild')")
                self.conn.commit()
            self.conn.execute("VACUUM")
        return {"memories": n_mem, "ofrendas": n_ofr}
