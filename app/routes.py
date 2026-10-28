"""HTTP API. All routes live under /api."""
import datetime
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app import __version__, llm, prompts, retrieval
from app.config import SUPPORTED_MODELS

router = APIRouter(prefix="/api")


def _clean(value):
    return value.strip() if isinstance(value, str) else value


class MemoryIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=80, description="Person, pet, place, or project")
    text: str = Field(min_length=1, max_length=2000)
    tags: str = Field(default="", max_length=200)
    date: str = Field(default="", max_length=10)

    _strip = field_validator("title", "subject", "text", "tags", "date", mode="before")(_clean)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return ", ".join(parts[:10])

    @field_validator("date")
    @classmethod
    def _date(cls, v):
        if v:
            try:
                datetime.date.fromisoformat(v)
            except ValueError:
                raise ValueError("date must look like YYYY-MM-DD") from None
        return v


class SettingsIn(BaseModel):
    model: str = Field(pattern=r"^[A-Za-z0-9._\-/:]{1,100}$")
    ollama_url: str = Field(min_length=8, max_length=200)

    _strip = field_validator("model", "ollama_url", mode="before")(_clean)

    @field_validator("ollama_url")
    @classmethod
    def _url(cls, v):
        if not re.match(r"^https?://[^\s]+$", v):
            raise ValueError("ollama_url must start with http:// or https://")
        return v.rstrip("/")


class OfrendaIn(BaseModel):
    subject: str = Field(min_length=1, max_length=80)
    _strip = field_validator("subject", mode="before")(_clean)


class SeanceIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    subject: str | None = Field(default=None, max_length=80)
    _strip = field_validator("question", "subject", mode="before")(_clean)


def runtime(request: Request):
    db, cfg = request.app.state.db, request.app.state.settings
    model = db.get_setting("model") or cfg.model
    url = db.get_setting("ollama_url") or cfg.ollama_url
    return db, cfg, model, url


def _fail(status, code, message):
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _public(m):
    keys = ("id", "title", "subject", "date", "text", "tags", "score")
    return {k: m[k] for k in keys if k in m}


# ---- status & settings --------------------------------------------------
@router.get("/health")
def health(request: Request):
    db, _cfg, model, url = runtime(request)
    info = {"version": __version__, "model": model, "ollama_url": url, "ollama": False,
            "model_installed": False, "installed_models": [], "memories": db.count_memories()}
    try:
        installed = llm.list_models(url)
        info.update(ollama=True, installed_models=installed,
                    model_installed=llm.is_installed(model, installed))
        if not info["model_installed"]:
            info["message"] = f"Model '{model}' is not installed. Run: ollama pull {model}"
    except llm.LLMError as exc:
        info["message"] = exc.message
    return info


@router.get("/settings")
def get_settings(request: Request):
    _db, cfg, model, url = runtime(request)
    return {"model": model, "ollama_url": url, "supported_models": list(SUPPORTED_MODELS),
            "top_k": cfg.top_k}


@router.put("/settings")
def put_settings(body: SettingsIn, request: Request):
    db = request.app.state.db
    db.set_setting("model", body.model)
    db.set_setting("ollama_url", body.ollama_url)
    return get_settings(request)


# ---- memories -----------------------------------------------------------
@router.get("/memories")
def list_memories(request: Request, subject: str | None = None):
    return request.app.state.db.list_memories(subject)


@router.post("/memories", status_code=201)
def create_memory(body: MemoryIn, request: Request):
    return request.app.state.db.add_memory(**body.model_dump())


@router.put("/memories/{memory_id}")
def update_memory(memory_id: int, body: MemoryIn, request: Request):
    row = request.app.state.db.update_memory(memory_id, **body.model_dump())
    if row is None:
        raise _fail(404, "not_found", "That memory no longer exists.")
    return row


@router.delete("/memories/{memory_id}")
def delete_memory(memory_id: int, request: Request):
    if not request.app.state.db.delete_memory(memory_id):
        raise _fail(404, "not_found", "That memory no longer exists.")
    return {"deleted": memory_id}


@router.get("/subjects")
def subjects(request: Request):
    return request.app.state.db.subjects()


@router.delete("/data")
def delete_everything(request: Request, confirm: str = ""):
    if confirm != "yes":
        raise _fail(400, "confirmation_required", "Add ?confirm=yes to delete all data.")
    return {"deleted": request.app.state.db.delete_all()}


# ---- ofrenda ------------------------------------------------------------
@router.post("/ofrenda", status_code=201)
def make_ofrenda(body: OfrendaIn, request: Request):
    db, cfg, model, url = runtime(request)
    memories = db.list_memories(body.subject, limit=cfg.top_k)
    if not memories:
        raise _fail(404, "no_memories", f"No saved memories for '{body.subject}'. Add some first.")
    messages = prompts.ofrenda_messages(memories[0]["subject"], memories)
    parsed, last_error = None, None
    for _attempt in range(2):  # small models sometimes emit broken JSON; retry once
        raw = llm.chat(messages, model, url, json_mode=True, timeout=cfg.timeout, max_tokens=500)
        try:
            parsed = llm.parse_ofrenda(raw)
            break
        except llm.BadLLMOutput as exc:
            last_error = exc
    if parsed is None:
        raise last_error
    saved = db.add_ofrenda(memories[0]["subject"], parsed["remembrance"], parsed["remembered"],
                           parsed["closing"], model, [m["id"] for m in memories])
    saved["sources"] = [_public(m) for m in memories]
    return saved


@router.get("/ofrendas")
def list_ofrendas(request: Request):
    return request.app.state.db.list_ofrendas()


@router.delete("/ofrendas/{ofrenda_id}")
def delete_ofrenda(ofrenda_id: int, request: Request):
    if not request.app.state.db.delete_ofrenda(ofrenda_id):
        raise _fail(404, "not_found", "That ofrenda no longer exists.")
    return {"deleted": ofrenda_id}


# ---- séance -------------------------------------------------------------
@router.post("/seance")
def seance(body: SeanceIn, request: Request):
    db, cfg, model, url = runtime(request)
    base = {"disclaimer": prompts.DISCLAIMER, "model": model, "sources": []}
    if db.count_memories() == 0:
        return {**base, "answered": False, "reason": "empty", "answer": prompts.NO_MEMORIES_TEXT}
    hits = retrieval.retrieve(db, body.question, body.subject, cfg.top_k)
    if not hits:  # nothing relevant: refuse without bothering the model
        return {**base, "answered": False, "reason": "no_relevant_memory",
                "answer": prompts.NO_ANSWER_TEXT}
    raw = llm.chat(prompts.seance_messages(body.question, hits), model, url,
                   timeout=cfg.timeout, max_tokens=300)
    if prompts.NO_ANSWER_TOKEN in raw:
        return {**base, "answered": False, "reason": "model_declined",
                "answer": prompts.NO_ANSWER_TEXT}
    return {**base, "answered": True, "answer": raw, "sources": [_public(m) for m in hits]}
