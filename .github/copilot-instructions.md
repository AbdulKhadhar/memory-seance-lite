# Instructions for AI assistants working on this repo

Memory Séance Lite is a local-first memorial app. Keep it that way.

- Never add cloud APIs, API keys, telemetry, analytics, or external fonts/scripts. The only network call is to the user's Ollama URL.
- Keep runtime dependencies at `fastapi`, `uvicorn`, `httpx` unless there is a very strong reason.
- Generated text must stay grounded in retrieved memories. The séance narrator speaks in the third person and never as the person remembered.
- Tests must mock every LLM call (`app.llm.chat`) and use a temporary SQLite file. Run `ruff check .` and `pytest -q`.
- Never put real personal memories in tests, docs or examples. Use fictional data only.
- Frontend is vanilla JS: build DOM with `textContent` (see `el()` in `static/js/app.js`), no inline styles or scripts (strict CSP).
