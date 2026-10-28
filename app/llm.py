"""Thin Ollama client. Only talks to the base URL you configure (default: localhost)."""
import json
import re

import httpx


class LLMError(Exception):
    code = "llm_error"
    status = 502

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class OllamaUnavailable(LLMError):
    code = "ollama_unavailable"
    status = 503


class ModelNotInstalled(LLMError):
    code = "model_missing"
    status = 409


class LLMTimeout(LLMError):
    code = "llm_timeout"
    status = 504


class BadLLMOutput(LLMError):
    code = "llm_bad_output"
    status = 502


def strip_think(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()


def is_installed(model, installed):
    return model in installed or f"{model}:latest" in installed


def _unavailable(base_url):
    return OllamaUnavailable(
        f"Cannot reach Ollama at {base_url}. Start it with `ollama serve` (or open the Ollama app)."
    )


def list_models(base_url, client=None, timeout=5.0):
    owns = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        resp = client.get(f"{base_url.rstrip('/')}/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise _unavailable(base_url) from None
    finally:
        if owns:
            client.close()


def chat(messages, model, base_url, *, json_mode=False, timeout=120.0, max_tokens=400, client=None):
    # Resource and memory optimized options:
    # - num_ctx: 2048 prevents unbounded KV cache memory consumption
    # - num_predict: bounds generated token buffer
    # - num_batch: 128 reduces peak memory during prompt evaluation
    # - keep_alive: '5m' frees RAM/VRAM after 5 minutes of inactivity instead of staying loaded indefinitely
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "5m",
        "options": {
            "temperature": 0.3,
            "num_ctx": 2048,
            "num_predict": max_tokens,
            "num_batch": 128,
        },
    }
    if json_mode:
        payload["format"] = "json"
    if model.startswith("qwen3") or model.startswith("qwen2"):
        payload["think"] = False  # skip the slow reasoning trace on tiny machines
    owns = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        resp = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
    except httpx.TimeoutException:
        raise LLMTimeout(
            f"The model '{model}' took longer than {int(timeout)}s. Try the smaller qwen3:0.6b model."
        ) from None
    except httpx.HTTPError:
        raise _unavailable(base_url) from None
    finally:
        if owns:
            client.close()

    if resp.status_code == 404 and "not found" in resp.text.lower():
        raise ModelNotInstalled(f"Model '{model}' is not installed. Run: ollama pull {model}")
    if resp.status_code >= 400:
        raise LLMError(f"Ollama returned HTTP {resp.status_code}. Check the Ollama URL in Settings.")
    try:
        content = resp.json()["message"]["content"]
    except (ValueError, KeyError, TypeError):
        raise BadLLMOutput("Ollama sent a response this app could not read.") from None
    content = strip_think(content)
    if not content:
        raise BadLLMOutput("The model returned an empty answer. Please try again.")
    return content


def parse_ofrenda(raw):
    """Validate the model's JSON. Raises BadLLMOutput if it is unusable."""
    text = raw.strip()
    try:
        data = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        try:
            data = json.loads(text[start : end + 1]) if 0 <= start < end else None
        except ValueError:
            data = None
    if not isinstance(data, dict):
        raise BadLLMOutput("The model did not return a usable ofrenda. Please try again.")
    remembrance = data.get("remembrance")
    closing = data.get("closing")
    items = data.get("remembered")
    if isinstance(items, str):
        items = [items]
    if not (isinstance(remembrance, str) and remembrance.strip() and isinstance(closing, str)
            and closing.strip() and isinstance(items, list)):
        raise BadLLMOutput("The model's ofrenda was missing required parts. Please try again.")
    items = [str(i).strip() for i in items if str(i).strip()][:3]
    if not items:
        raise BadLLMOutput("The model's ofrenda had no remembered items. Please try again.")
    return {"remembrance": remembrance.strip(), "remembered": items, "closing": closing.strip()}
