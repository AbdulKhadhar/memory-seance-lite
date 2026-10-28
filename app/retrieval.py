"""Lightweight retrieval: SQLite FTS5 (BM25) with a pure-Python fallback."""
import re
import sqlite3

STOPWORDS = frozenset(
    """a about after all also am an and any are as at be been being but by can could did do does
    doing for from had has have having he her hers him his how i if in into is it its just me my
    of on or our out she so some than that the their them then there these they this those to
    too us was we were what when where which who whom why will with would you your tell told
    say said remember remembered el la los las de del que un una y en es por con para su sus mi
    como qué quién cuándo dónde""".split()
)


def tokenize(text):
    return [t for t in re.findall(r"\w+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


def fts_query(tokens, max_terms=12):
    unique = list(dict.fromkeys(tokens))[:max_terms]
    return " OR ".join(f'"{t}"' for t in unique)


def _stem(token):
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def _fallback(memories, tokens, k):
    wanted = {_stem(t) for t in tokens}
    scored = []
    for m in memories:
        strong = {_stem(t) for t in tokenize(f"{m['title']} {m['subject']} {m['tags']}")}
        body = {_stem(t) for t in tokenize(m["text"])}
        score = 2 * len(wanted & strong) + len(wanted & body)
        if score:
            scored.append({**m, "score": float(score)})
    scored.sort(key=lambda m: (-m["score"], -m["id"]))
    return scored[:k]


def retrieve(db, question, subject=None, k=4):
    """Return up to k memories relevant to the question; an empty list means 'no match'."""
    k = max(1, min(int(k), 5))
    tokens = tokenize(question)
    if not tokens:
        return []
    if db.fts_enabled:
        try:
            return db.search_fts(fts_query(tokens), k, subject)
        except sqlite3.OperationalError:
            pass
    return _fallback(db.list_memories(subject), tokens, k)
