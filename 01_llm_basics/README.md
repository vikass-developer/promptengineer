# 01 · LLM basics: tokens, context, temperature, embeddings

**Exercise:** explain LLM architecture in your own words. Write it in [my_explanation.md](my_explanation.md).

Read the primer, run the demos, then write your explanation *without looking back at this page*. If you can't explain a part, that's the part to re-read.

```powershell
..\.venv\Scripts\python explore.py            # all four demos
..\.venv\Scripts\python explore.py tokens     # or: temperature | context | embeddings
```

---

## Primer

### The pipeline, end to end

```
text ─► tokenizer ─► token IDs ─► embedding lookup ─► N × transformer block ─► logits ─► sampling ─► next token
                                                       (self-attention + MLP)                          │
        ▲──────────────────────────── append token, repeat ───────────────────────────────────────────┘
```

1. **Tokenizer.** Splits text into *tokens*, which are sub-word pieces from a fixed vocabulary of about 30k to 200k entries. `"antidisestablishmentarianism"` becomes several tokens and `" the"` is one. Billing, rate limits, and context windows are all counted in tokens, not characters or words. English averages roughly 4 characters per token. Other languages and code are often less efficient.
2. **Embedding lookup.** Each token ID maps to a learned vector (for example 3072 numbers in `llama3.2:3b`). Position information is added so the model knows word order.
3. **Transformer blocks** (stacked 20 to 100+ times):
   - **Self-attention:** every token looks at every *earlier* token and decides how much each one matters to it. This is how "it" gets linked to the noun it refers to. The cost grows with context length.
   - **MLP (feed-forward):** a per-token transformation where much of the "knowledge" is stored.
4. **Logits.** The final vector is projected to one score per vocabulary entry.
5. **Sampling.** The scores become probabilities (softmax), and one token is picked. That token is appended and the whole loop runs again. This is **autoregressive generation**: one token at a time, and each new token depends on all the previous ones.

The model has no memory between calls. Anything it "remembers" in a chat is there because the client sends the whole conversation again every turn.

### Context window

- The context window is the maximum number of tokens the model can attend to at once: **prompt + conversation history + output**.
- Going past the limit means something gets cut. Ollama truncates the prompt silently, as the `context` demo shows. Hosted APIs usually return an error instead.
- A longer context costs more (attention cost grows with length), runs slower, and is not always used well. Facts buried in the middle are recalled worse than facts at the start or end.
- The **KV cache** stores attention state for a prefix that has already been processed, so a repeated prefix (like a system prompt) is cheap. Ollama reports this as `prompt_eval_cached_count`.

### Temperature and sampling

- **Temperature** divides the logits before softmax. A low value (around 0) makes the distribution sharper, so you get the most likely token almost every time: deterministic and repetitive. A high value (above 1) flattens it, giving more variety and more mistakes.
- **top_p / top_k** sample only from the most likely tokens (the top-p probability mass, or the k best). They cut off the long tail of unlikely tokens.
- **seed** makes sampling repeatable on the same model and hardware.
- Rule of thumb: use **0 to 0.3** for extraction, classification, and code, and **0.7 to 1.0** for brainstorming and creative writing.

### Embeddings

- An **embedding model** maps a whole piece of text to one fixed-length vector (768 dimensions for `nomic-embed-text`). Texts with similar *meaning* end up close together, even if they share no words.
- Closeness is usually measured with **cosine similarity**, from -1 to 1.
- Uses: semantic search, RAG retrieval, clustering, deduplication, and classification by nearest example.
- These vectors are not the per-token embeddings inside a chat model. The idea is the same, but the model is different and trained for a different goal.

---

## Questions your explanation should answer

- [ ] What is a token, and why do tokens (not words) set cost and limits?
- [ ] What happens, step by step, between "prompt in" and "one word out"?
- [ ] Why does generation happen one token at a time, and what does that mean for latency?
- [ ] What fills up the context window, and what happens when it overflows?
- [ ] What does temperature change *mechanically*, and when would you use 0 versus 1?
- [ ] What is an embedding, and how is it different from generating text?
- [ ] Why does a chatbot "forget" unless the client re-sends history?
