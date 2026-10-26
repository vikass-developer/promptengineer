"""Exercise: run a local model and integrate with it over its HTTP API.

Ollama serves a REST API on http://localhost:11434. This script calls it directly with httpx, so
you can see what every SDK wraps:

  GET  /api/tags      list installed models
  POST /api/chat      chat (with options, streaming, JSON-schema output)
  POST /api/embed     embeddings
  POST /v1/chat/...   OpenAI-compatible endpoint, so any OpenAI SDK or tool works unchanged

Usage:  python ollama_api.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import CHAT_MODEL, EMBED_MODEL, OLLAMA_URL  # noqa: E402


def list_models():
    print("=== GET /api/tags: installed models ===")
    for m in httpx.get(f"{OLLAMA_URL}/api/tags").json()["models"]:
        d = m["details"]
        print(f"  {m['name']:<26} {d['parameter_size']:>6}  {d['quantization_level']:<7} {m['size'] / 1e9:.1f} GB  {m.get('capabilities')}")


def chat_once():
    print("\n=== POST /api/chat: one request, one response ===")
    body = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "You answer in one sentence."},
            {"role": "user", "content": "Why would a company run an LLM locally instead of using a cloud API?"},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 80},
        "keep_alive": "10m",  # how long the model stays loaded in memory after this call
    }
    data = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600).json()
    print(f"  {data['message']['content']}")
    print(f"  prompt tokens={data['prompt_eval_count']} output tokens={data['eval_count']} "
          f"load={data['load_duration'] / 1e9:.1f}s total={data['total_duration'] / 1e9:.1f}s")


def chat_streaming():
    print("\n=== POST /api/chat with stream=true: tokens as they are generated ===")
    body = {
        "model": CHAT_MODEL,
        "messages": [{"role": "user", "content": "List three uses of embeddings, one line each."}],
        "options": {"temperature": 0, "num_predict": 120},
    }  # stream defaults to true: the response is one JSON object per line
    start = time.perf_counter()
    first_token_at = None
    print("  ", end="")
    with httpx.stream("POST", f"{OLLAMA_URL}/api/chat", json=body, timeout=600) as resp:
        for line in resp.iter_lines():
            chunk = json.loads(line)
            if first_token_at is None:
                first_token_at = time.perf_counter() - start
            print(chunk["message"]["content"].replace("\n", "\n  "), end="", flush=True)
            if chunk["done"]:
                speed = chunk["eval_count"] / (chunk["eval_duration"] / 1e9)
    print(f"\n  time to first token={first_token_at:.2f}s  total={time.perf_counter() - start:.1f}s  speed={speed:.1f} tok/s")
    print("  -> Streaming doesn't make generation faster. It lets the user start reading after the first token.")


def chat_json_schema():
    print("\n=== POST /api/chat with format=<JSON schema>: constrained output ===")
    schema = {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "country": {"type": "string"},
            "population_millions": {"type": "number"},
        },
        "required": ["city", "country", "population_millions"],
    }
    body = {
        "model": CHAT_MODEL,
        "messages": [{"role": "user", "content": "Tell me about the capital of Japan."}],
        "format": schema,  # Ollama restricts sampling so the output must match this schema
        "stream": False,
        "options": {"temperature": 0},
    }
    data = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600).json()
    parsed = json.loads(data["message"]["content"])
    print(f"  {parsed}")
    print("  -> The schema guarantees the shape, not the facts. That is why exercise 03 also validates content.")


def embeddings():
    print("\n=== POST /api/embed: vectors for semantic search ===")
    data = httpx.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": ["local LLM", "on-device AI"]}, timeout=300).json()
    vectors = data["embeddings"]
    print(f"  {len(vectors)} vectors x {len(vectors[0])} dims; first 5 values: {[round(v, 3) for v in vectors[0][:5]]}")


def openai_compatible():
    print("\n=== OpenAI SDK pointed at Ollama's /v1 endpoint ===")
    from openai import OpenAI

    client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")  # key is required by the SDK but ignored
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": "Say 'hello from a local model' and nothing else."}],
        temperature=0,
    )
    print(f"  {resp.choices[0].message.content}  (usage: {resp.usage.prompt_tokens} in / {resp.usage.completion_tokens} out)")
    print("  -> Code written for a cloud API can switch to local by changing base_url and model.")


if __name__ == "__main__":
    try:
        httpx.get(f"{OLLAMA_URL}/api/version", timeout=3).raise_for_status()
    except httpx.HTTPError:
        sys.exit(f"Ollama is not reachable at {OLLAMA_URL}. Start the Ollama app, then retry.")
    list_models()
    chat_once()
    chat_streaming()
    chat_json_schema()
    embeddings()
    openai_compatible()
