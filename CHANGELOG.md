# Changelog

## 0.1.0

First release.

- Add, edit, list and delete memories (title, subject, text, tags, date) in a local SQLite file.
- Retrieval with SQLite FTS5 (BM25) and a pure-Python fallback; 3 to 5 memories per request.
- Ofrenda generation (remembrance, three remembered items, closing line), saved locally.
- Memory séance chat that answers only from retrieved memories and shows its sources.
- Refusal without calling the model when no relevant memory exists.
- Settings for model (gemma3:1b, qwen3:0.6b, or any installed model) and Ollama URL.
- "Delete all memories" with database compaction.
- Mocked-LLM pytest suite, ruff linting, CI workflow and a manual demo-report workflow.
