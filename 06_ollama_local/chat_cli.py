"""A minimal streaming chat app on top of the local Ollama API. It keeps history client-side,
because the model itself remembers nothing between calls.

Usage:  python chat_cli.py [--model llama3.2:3b] [--system "You are a pirate."]
Commands:  /reset  clear history    /tokens  show context usage    /quit
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import CHAT_MODEL, OLLAMA_URL  # noqa: E402

NUM_CTX = 4096


def stream_reply(model: str, messages: list[dict]) -> tuple[str, int]:
    """Stream the assistant's reply to the terminal. Returns (text, context tokens now in use)."""
    body = {"model": model, "messages": messages, "options": {"num_ctx": NUM_CTX, "temperature": 0.7}}
    reply, context_tokens = [], 0
    with httpx.stream("POST", f"{OLLAMA_URL}/api/chat", json=body, timeout=600) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            chunk = json.loads(line)
            piece = chunk["message"]["content"]
            reply.append(piece)
            print(piece, end="", flush=True)
            if chunk["done"]:
                context_tokens = chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0)
    print()
    return "".join(reply), context_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=CHAT_MODEL)
    parser.add_argument("--system", default="You are a concise, helpful assistant.")
    args = parser.parse_args()

    def fresh_history():
        return [{"role": "system", "content": args.system}]

    history, used = fresh_history(), 0
    print(f"Chatting with {args.model} (context window {NUM_CTX} tokens). /reset, /tokens, /quit")
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user in ("", "/quit"):
            break
        if user == "/reset":
            history, used = fresh_history(), 0
            print("(history cleared)")
            continue
        if user == "/tokens":
            print(f"(conversation uses about {used}/{NUM_CTX} tokens of context)")
            continue
        history.append({"role": "user", "content": user})
        print("bot> ", end="")
        reply, used = stream_reply(args.model, history)
        history.append({"role": "assistant", "content": reply})
        if used > NUM_CTX * 0.8:
            print(f"(warning: {used}/{NUM_CTX} context tokens used; older messages will soon be cut off. Try /reset)")


if __name__ == "__main__":
    main()
