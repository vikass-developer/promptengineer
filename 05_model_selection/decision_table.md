# Model selection decision table

**Exercise:** create a model-selection decision table. This is a starting version. Replace the
*measured* rows with your own numbers from `python benchmark.py` (see [results/benchmark.md](results/benchmark.md)),
and fill in current cloud prices from the providers' pricing pages. Prices change often, so they are deliberately left blank here.

## How to choose (in this order)

1. **Hard constraints first.** These filter options out; they are not trade-offs.
   - Data may not leave our machines or network (PII, health, legal, client NDA) → **local only**.
   - Must work offline or air-gapped → **local only**.
   - Hard budget per request or per month → rule out tiers above it.
2. **Quality bar.** Write 20 to 50 real examples of *your* task with expected outputs (like the checks in `benchmark.py` or exercise 03).
   Run them against each remaining option. Ignore public leaderboards for this step.
3. **Cheapest and fastest option that passes** the bar wins. Re-run the evals when models or prompts change.

## Option comparison

|  | Local small<br>`llama3.2:3b` | Local mid<br>`qwen2.5:7b` | Hosted fast<br>(e.g. Claude Haiku 5.5) | Hosted balanced<br>(e.g. Claude Sonnet 5.5) | Hosted frontier<br>(e.g. Claude Opus 5.5) |
|---|---|---|---|---|---|
| **Quality: simple tasks** (classify, extract) | OK, needs validation and retries | Good | Very good | Excellent | Excellent |
| **Quality: reasoning, multi-step agents** | Weak | Fair | Good | Very good | Best |
| **Structured output and tool calling** | Flaky (see ex. 03/04) | Mostly reliable with retries | Reliable | Reliable | Reliable |
| **Latency on this laptop** *(measured 2026-10-23, CPU only)* | 2.5 s avg, ~19 tok/s | 5.1 s avg, ~11 tok/s | network + fast | network + medium | network + slower |
| **Cold start** *(measured)* | 9.7 s | 25.8 s | none | none | none |
| **Benchmark tasks passed** *(measured)* | 2/3: failed "3 pens for 2 €, cost of 12?" | 2/3: same failure | _run your evals_ | _run your evals_ | _run your evals_ |
| **Context window** | 128k max (Ollama default 4k) | 32k max (Ollama default 4k) | large: check docs | large: check docs | large: check docs |
| **Cost per 1M input / output tokens** | $0 marginal (hardware + power) | $0 marginal | _fill: low_ | _fill: medium_ | _fill: high_ |
| **Privacy** | Data never leaves the machine | Data never leaves the machine | Sent to provider: check retention terms | same | same |
| **Works offline** | Yes | Yes | No | No | No |
| **Ops burden** | You run, update and scale it | same | API key, rate limits | same | same |
| **Scales to many users** | Limited by your hardware | Limited by your hardware | Yes | Yes | Yes |

## Decide by scenario

| Scenario | Pick | Why |
|---|---|---|
| Learning, prototyping, experiments | Local mid | Free, private, unlimited retries; fine quality for practice |
| Documents with PII, health or legal data, or under NDA | Local mid (larger local model if quality falls short) | Privacy is a hard constraint, so cloud is ruled out before quality matters |
| High-volume, simple classification or routing (100k+ per day) | Hosted fast, or local if volume is steady and the hardware exists | Cost per call dominates. The simplest model that passes evals wins |
| Customer-facing chat with a sub-second first token | Hosted fast, with streaming | CPU-only local models are too slow for interactive use, as the benchmark shows |
| Agent with many tools and multi-step plans | Hosted balanced or frontier | Small models mis-call tools and lose track of the plan |
| Hard reasoning, complex code, high-stakes answers | Hosted frontier | Quality matters more than cost; each mistake is expensive |
| Long documents (100+ pages) in one prompt | Hosted with a large context | A local 4k–32k context on CPU is slow and truncates |
| Embeddings for search or RAG | Local `nomic-embed-text` | Small, fast on CPU, private, and good enough for most retrieval |

## A common production pattern: route by difficulty

Send each request to the cheapest model likely to handle it, and escalate when validation fails:

```
request ─► local / hosted-fast model ─► Pydantic validation passes? ──yes──► done
                                                │ no (after retries)
                                                ▼
                                       hosted balanced / frontier
```

This is exercise 03's retry loop with a fallback model added at the end.
