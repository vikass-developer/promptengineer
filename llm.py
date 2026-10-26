"""Shared plumbing for every exercise: Ollama settings, raw-API helpers, and a Pydantic AI model factory.

Override any setting with an environment variable, e.g.  CHAT_MODEL=llama3.2:3b
"""
import os
import sys
import time
from dataclasses import dataclass

import httpx

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:7b")
SMALL_MODEL = os.getenv("SMALL_MODEL", "llama3.2:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


@dataclass
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    output_tokens: int
    seconds: float  # wall clock, including any model load time
    load_seconds: float  # time Ollama spent loading the model into memory
    tokens_per_second: float  # generation speed as measured by Ollama


def chat(messages: list[dict], model: str = CHAT_MODEL, **options) -> ChatResult:
    """One non-streaming call to Ollama's native /api/chat.

    `options` are Ollama sampling/runtime options: temperature, top_p, top_k, seed,
    num_ctx (context window), num_predict (max output tokens), stop, ...
    """
    start = time.perf_counter()
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": model, "messages": messages, "stream": False, "options": options},
        timeout=900,
    )
    resp.raise_for_status()
    data = resp.json()
    eval_seconds = (data.get("eval_duration") or 1) / 1e9
    return ChatResult(
        text=data["message"]["content"],
        model=model,
        prompt_tokens=data.get("prompt_eval_count", 0),
        output_tokens=data.get("eval_count", 0),
        seconds=time.perf_counter() - start,
        load_seconds=data.get("load_duration", 0) / 1e9,
        tokens_per_second=data.get("eval_count", 0) / eval_seconds,
    )


def ask(prompt: str, system: str | None = None, model: str = CHAT_MODEL, **options) -> ChatResult:
    """Convenience wrapper: optional system message + one user message."""
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    return chat(messages, model=model, **options)


def count_tokens(text: str, model: str = SMALL_MODEL) -> int:
    """Ollama has no tokenize endpoint, so we send the raw text (no chat template) and read
    back how many prompt tokens it evaluated, minus the 1 beginning-of-sequence token."""
    resp = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": text, "raw": True, "stream": False, "options": {"num_predict": 1}},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["prompt_eval_count"] - 1


def embed(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    resp = httpx.post(f"{OLLAMA_URL}/api/embed", json={"model": model, "input": texts}, timeout=300)
    resp.raise_for_status()
    return resp.json()["embeddings"]


def unload(model: str) -> None:
    """Evict a model from memory, so the next call measures a true cold start."""
    httpx.post(f"{OLLAMA_URL}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60).raise_for_status()


def installed_models() -> list[dict]:
    resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
    resp.raise_for_status()
    return resp.json()["models"]


def pydantic_ai_model(model_name: str = CHAT_MODEL):
    """Pydantic AI talks to Ollama through Ollama's OpenAI-compatible /v1 endpoint."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.ollama import OllamaProvider

    return OpenAIChatModel(model_name, provider=OllamaProvider(base_url=f"{OLLAMA_URL}/v1"))
