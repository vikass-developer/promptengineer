"""Hands-on demos for tokens, temperature, the context window and embeddings.

Usage:  python explore.py [tokens|temperature|context|embeddings]   (no argument = all)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import SMALL_MODEL, ask, count_tokens, embed  # noqa: E402


def demo_tokens():
    print("\n=== TOKENS: the unit of cost and limits ===")
    samples = [
        "hello",
        "Hello, world!",
        "Tokenization splits text into subword units.",
        "antidisestablishmentarianism",
        "def add(a, b): return a + b",
        "{\"order_id\": \"ORD-10422\", \"status\": \"shipped\"}",
        "नमस्ते, आप कैसे हैं?",  # Hindi: "Hello, how are you?"
        "2026-10-23T08:09:39Z",
    ]
    print(f"(tokenizer of {SMALL_MODEL})")
    print(f"{'tokens':>6} {'chars':>6} {'chars/token':>11}  text")
    for text in samples:
        n = count_tokens(text)
        print(f"{n:>6} {len(text):>6} {len(text) / n:>11.1f}  {text}")
    print("-> English prose is about 4 chars/token. Code, JSON, timestamps and non-Latin scripts cost more per character.")


def demo_temperature():
    print("\n=== TEMPERATURE: same prompt, different randomness ===")
    prompt = "Invent a name for a small coffee shop. Reply with the name only."
    for temperature in (0.0, 0.8, 1.5):
        names = [
            ask(prompt, model=SMALL_MODEL, temperature=temperature, seed=seed, num_predict=12).text.strip()
            for seed in (1, 2, 3, 4)
        ]
        print(f"temperature={temperature:<4} unique={len(set(names))}/4  {names}")
    print("-> At 0 the model nearly always picks the top token, so different seeds give the same answer.")


def demo_context():
    print("\n=== CONTEXT WINDOW: what happens when the prompt doesn't fit ===")
    filler = "The warehouse inventory report lists pallets, crates and shelving units in aisle order. " * 60
    prompt = f"The secret code is PURPLE-42.\n\n{filler}\n\nWhat is the secret code? Answer with the code only."
    print(f"prompt is about {count_tokens(prompt)} tokens; the code is in the first sentence")
    for num_ctx in (512, 4096):
        result = ask(prompt, model=SMALL_MODEL, temperature=0, num_ctx=num_ctx, num_predict=15)
        print(f"num_ctx={num_ctx:<5} prompt tokens actually seen={result.prompt_tokens:<5} answer={result.text.strip()!r}")
    print("-> With num_ctx=512 Ollama silently drops the start of the prompt, so the model never sees the code.")


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def demo_embeddings():
    print("\n=== EMBEDDINGS: meaning as a vector ===")
    docs = [
        "How do I reset my password?",
        "I forgot my login credentials and can't sign in.",
        "What time does the store open on Sundays?",
        "Our opening hours are 9am to 5pm, seven days a week.",
        "The cat is sleeping on the windowsill.",
    ]
    vectors = embed(docs)
    print(f"each text -> a vector of {len(vectors[0])} numbers")
    print("\ncosine similarity (1.0 = same meaning):")
    print("      " + "".join(f"  [{i}]" for i in range(len(docs))))
    for i, row in enumerate(vectors):
        print(f"  [{i}] " + "".join(f" {cosine(row, col):.2f}" for col in vectors) + f"   {docs[i]}")

    query = "account locked out, need to log in"
    query_vec = embed([query])[0]
    ranked = sorted(((cosine(query_vec, v), d) for v, d in zip(vectors, docs)), reverse=True)
    print(f"\nsemantic search for {query!r}:")
    for score, doc in ranked[:3]:
        print(f"  {score:.2f}  {doc}")
    print("-> [0] and [1] share almost no words but land close together. That is the basis of semantic search and RAG.")


DEMOS = {
    "tokens": demo_tokens,
    "temperature": demo_temperature,
    "context": demo_context,
    "embeddings": demo_embeddings,
}

if __name__ == "__main__":
    chosen = sys.argv[1:] or list(DEMOS)
    for name in chosen:
        DEMOS[name]()
