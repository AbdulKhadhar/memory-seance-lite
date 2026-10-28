"""Load the fictional sample memories in docs/sample-memories.json into your local database.

Usage: python scripts/load_sample.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.database import Database  # noqa: E402


def main():
    settings = load_settings()
    db = Database(settings.db_path)
    items = json.loads((ROOT / "docs" / "sample-memories.json").read_text(encoding="utf-8"))
    for item in items:
        db.add_memory(item["title"], item["subject"], item["text"], item.get("tags", ""), item.get("date", ""))
    print(f"Loaded {len(items)} sample memories into {settings.db_path}")


if __name__ == "__main__":
    main()
