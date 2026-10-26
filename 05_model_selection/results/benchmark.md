# Local model benchmark

Temperature 0, same prompts for every model. *Cold start* = time to load the model into memory on first use.

## Summary

| Model | Size on disk | Cold start | Avg latency (warm) | Gen speed | Tasks passed |
|---|---:|---:|---:|---:|---:|
| qwen2.5:7b | 4.7 GB | 25.8 s | 5.1 s | 11.3 tok/s | 2/3 |
| llama3.2:3b | 2.0 GB | 9.7 s | 2.5 s | 19.2 tok/s | 2/3 |

## Per task

| Model | Task | Check | Result | Seconds | Output |
|---|---|---|---|---:|---|
| qwen2.5:7b | classify | one allowed word | PASS | 29.0 | `Neutral` |
| qwen2.5:7b | extract-json | exact JSON fields | PASS | 8.3 | ````json {   "name": "Priya Nair",   "email": "priya.nair@example.com",   "order_` |
| qwen2.5:7b | reason | answer is 8 | FAIL | 1.9 | `4` |
| llama3.2:3b | classify | one allowed word | PASS | 11.3 | `Neutral` |
| llama3.2:3b | extract-json | exact JSON fields | PASS | 3.7 | `{"name": "Priya Nair", "email": "priya.nair@example.com", "order_id": "ORD-20931` |
| llama3.2:3b | reason | answer is 8 | FAIL | 1.2 | `4` |
