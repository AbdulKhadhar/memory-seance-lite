# Contributing

Thank you for helping. This project stays small on purpose: few dependencies, no build step, no cloud.

1. Fork and clone, then `pip install -r requirements-dev.txt`.
2. Make a branch and keep changes focused.
3. Run `ruff check .` and `pytest -q` before you push. Tests must mock every LLM call and use a temporary database.
4. Open a pull request that says what changed and why.

Please do not add: paid or hosted APIs, telemetry, large dependencies, or features that send memories off the machine.
Good first issues: translations of the UI, export/import of memories as JSON, accessibility fixes, better retrieval for non-English text.
Be kind. This app holds people's grief, and the code and discussions should respect that.
