# Prompt Engineer track · Module 1: LLM Fundamentals

Hands-on exercises for each topic. Everything runs **locally on Ollama**, with no API keys and no cost.

| # | Topic | Exercise | Where | Done when |
|---|---|---|---|---|
| 01 | LLM basics: tokens, context, temperature, embeddings | Explain LLM architecture in your own words | [01_llm_basics/](01_llm_basics/) | `my_explanation.md` answers every question in the folder README |
| 02 | Prompt engineering: system / user / context / output | Create 10 prompt variants and compare outputs | [02_prompt_engineering/](02_prompt_engineering/) | `results/comparison.md` scored, takeaways written |
| 03 | Structured output + JSON schemas | Build validated Pydantic AI responses | [03_structured_output/](03_structured_output/) | 5/5 tickets valid; you've compared `--mode native/tool/prompted` |
| 04 | Function / tool calling | Implement 3 safe local tools | [04_tool_calling/](04_tool_calling/) | `pytest` green; attack prompts refused in `agent.py` |
| 05 | Model selection: latency, cost, privacy | Create a model-selection decision table | [05_model_selection/](05_model_selection/) | `decision_table.md` filled with your measured numbers and current prices |
| 06 | Local LLM with Ollama | Run a local model and integrate via API | [06_ollama_local/](06_ollama_local/) | `ollama_api.py` runs; you've chatted via `chat_cli.py` |

## Setup (already done on this machine)

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# Ollama must be running, with these models pulled:
#   ollama pull qwen2.5:7b ; ollama pull llama3.2:3b ; ollama pull nomic-embed-text
```

## Running

Run each script from its own folder:

```powershell
cd 01_llm_basics;        ..\.venv\Scripts\python explore.py
cd 02_prompt_engineering; ..\.venv\Scripts\python variants.py
cd 03_structured_output;  ..\.venv\Scripts\python triage.py --mode native
cd 04_tool_calling;       ..\.venv\Scripts\python -m pytest -q ; ..\.venv\Scripts\python agent.py
cd 05_model_selection;    ..\.venv\Scripts\python benchmark.py
cd 06_ollama_local;       ..\.venv\Scripts\python ollama_api.py ; ..\.venv\Scripts\python chat_cli.py
```

Shared settings live in [llm.py](llm.py). Switch models with an environment variable, e.g.
`$env:CHAT_MODEL="llama3.2:3b"` to make everything faster at lower quality.

> This machine runs Ollama on **CPU only**, so a 7B model takes 20–60 s per answer. That is fine for
> learning, and it is a useful data point for exercise 05.

## Suggested order

01 → 06 → 02 → 03 → 04 → 05. Seeing the raw API (06) early makes everything else less magical,
and model selection (05) is easiest once you've felt the quality differences yourself.
