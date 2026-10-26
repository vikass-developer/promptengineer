"""Measure latency, speed and quality signals of every local chat model, to fill in the decision table.

Each model runs the same three tasks at temperature 0. The first call per model includes the time
to load it into memory (cold start), which is reported separately.

Usage:  python benchmark.py
Writes: results/benchmark.md
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import ask, installed_models, unload  # noqa: E402

TASKS = [
    {
        "name": "classify",
        "prompt": "Classify the sentiment of this review as positive, negative or neutral. Reply with one word.\n\n"
        "Review: The desk arrived two weeks late and one leg was scratched, but support sorted it out quickly.",
        "check": lambda out: out.strip().strip(".").lower() in {"positive", "negative", "neutral"},
        "check_label": "one allowed word",
    },
    {
        "name": "extract-json",
        "prompt": "Extract the fields as JSON with keys name, email, order_id. Reply with JSON only.\n\n"
        "Hi, this is Priya Nair (priya.nair@example.com). My order ORD-20931 hasn't shipped yet.",
        "check": lambda out: _json_matches(out, {"name": "Priya Nair", "email": "priya.nair@example.com", "order_id": "ORD-20931"}),
        "check_label": "exact JSON fields",
    },
    {
        "name": "reason",
        "prompt": "A shop sells pens at 3 for 2 euros. How much do 12 pens cost? Reply with the number of euros only.",
        "check": lambda out: out.strip().rstrip(".").removeprefix("€").removesuffix(" euros").strip() in {"8", "8.00", "8.0"},
        "check_label": "answer is 8",
    },
]


def _json_matches(text: str, expected: dict) -> bool:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
    except ValueError:
        return False
    return all(data.get(k) == v for k, v in expected.items())


def main():
    models = [m["name"] for m in installed_models() if "completion" in m.get("capabilities", ["completion"])]
    print(f"benchmarking: {models}")
    rows = []
    for model in models:
        size_gb = next(m["size"] for m in installed_models() if m["name"] == model) / 1e9
        for loaded in installed_models():
            unload(loaded["name"])
        for i, task in enumerate(TASKS):
            result = ask(task["prompt"], model=model, temperature=0, seed=1, num_predict=120)
            passed = task["check"](result.text)
            rows.append({
                "model": model,
                "size_gb": size_gb,
                "task": task["name"],
                "check": task["check_label"],
                "passed": passed,
                "seconds": result.seconds,
                "load_seconds": result.load_seconds if i == 0 else 0.0,
                "tok_per_s": result.tokens_per_second,
                "output": result.text.strip().replace("\n", " ")[:80],
            })
            print(f"  {model:<14} {task['name']:<13} {'PASS' if passed else 'FAIL'}  {result.seconds:5.1f}s  "
                  f"{result.tokens_per_second:5.1f} tok/s  {result.text.strip()[:50]!r}")

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    report = out_dir / "benchmark.md"
    report.write_text(render(rows), encoding="utf-8")
    print(f"\nwrote {report}")


def render(rows: list[dict]) -> str:
    lines = [
        "# Local model benchmark",
        "",
        "Temperature 0, same prompts for every model. *Cold start* = time to load the model into memory on first use.",
        "",
        "## Summary",
        "",
        "| Model | Size on disk | Cold start | Avg latency (warm) | Gen speed | Tasks passed |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model in dict.fromkeys(r["model"] for r in rows):
        mine = [r for r in rows if r["model"] == model]
        warm = [r["seconds"] for r in mine[1:]] or [mine[0]["seconds"]]
        lines.append(
            f"| {model} | {mine[0]['size_gb']:.1f} GB | {mine[0]['load_seconds']:.1f} s | {sum(warm) / len(warm):.1f} s | "
            f"{sum(r['tok_per_s'] for r in mine) / len(mine):.1f} tok/s | {sum(r['passed'] for r in mine)}/{len(mine)} |"
        )
    lines += ["", "## Per task", "", "| Model | Task | Check | Result | Seconds | Output |", "|---|---|---|---|---:|---|"]
    for r in rows:
        output = r["output"].replace("|", "\\|")
        lines.append(f"| {r['model']} | {r['task']} | {r['check']} | {'PASS' if r['passed'] else 'FAIL'} | {r['seconds']:.1f} | `{output}` |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
