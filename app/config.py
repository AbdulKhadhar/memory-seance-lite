"""Configuration: environment variables, an optional .env file, and defaults.

The model name and Ollama URL can also be changed at runtime from the Settings
tab; those choices are stored in SQLite and take precedence over these defaults.
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_MODELS = ("gemma3:1b", "qwen3:0.6b")


@dataclass(frozen=True)
class Settings:
    model: str
    ollama_url: str
    db_path: Path
    host: str
    port: int
    top_k: int
    timeout: float


def _load_env_file(path: Path) -> None:
    """Tiny .env reader (no python-dotenv dependency). Real env vars win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def load_settings() -> Settings:
    _load_env_file(ROOT / ".env")
    db_path = Path(os.environ.get("MSL_DB_PATH", "data/memory_seance.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    try:
        timeout = float(os.environ.get("MSL_TIMEOUT", "120"))
    except ValueError:
        timeout = 120.0
    return Settings(
        model=os.environ.get("MSL_MODEL", SUPPORTED_MODELS[0]).strip() or SUPPORTED_MODELS[0],
        ollama_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        db_path=db_path,
        host=os.environ.get("MSL_HOST", "127.0.0.1"),
        port=_int("MSL_PORT", 8000),
        top_k=max(3, min(5, _int("MSL_TOP_K", 4))),  # keep context small: 3-5 memories
        timeout=timeout,
    )
