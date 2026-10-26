"""Exercise: create 10 prompt variants and compare outputs.

Every variant does the same job (triage a support ticket) but changes one thing about how the
prompt is built: system role, task framing, context, output format, examples, constraints.
Temperature is 0 and the seed is fixed, so differences come from the prompt, not from randomness.

Usage:  python variants.py [--model llama3.2:3b] [--only 1,5,10]
Writes: results/comparison.md   (score each output there, by hand)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import CHAT_MODEL, chat  # noqa: E402

TICKET = """From: dana.r@example.com
Subject: still waiting!!!

Hi, I ordered the blue standing desk (order ORD-10422) on Oct 2 and paid for express shipping.
Tracking hasn't updated in 6 days and the desk was supposed to arrive last Friday. I work from home
and I'm using my kitchen counter right now. If it can't arrive by Monday I want a refund of the
express shipping fee at least, honestly I'm thinking about cancelling the whole order."""

# Background a support agent would know but the model doesn't
POLICY = """Shipping policy:
- Express orders not delivered by the promised date get an automatic refund of the express fee.
- Orders with no tracking update for 5+ days are escalated to the carrier as "possibly lost".
- Orders can be cancelled for a full refund until they are delivered."""

FEW_SHOT_TICKET = "My invoice INV-778 charged me twice for the same monitor. Please fix."
FEW_SHOT_ANSWER = """Summary: Customer was double-charged on invoice INV-778 for one monitor.
Priority: high
Next steps:
- Verify duplicate charge on INV-778
- Refund the duplicate payment and confirm by email"""

STRUCTURED_FORMAT = """Summary: <one sentence>
Priority: <low|medium|high|urgent>
Next steps:
- <step>
- <step>"""

# Each variant: what it changes, plus the messages it sends. {ticket} is filled in at run time.
VARIANTS = [
    {
        "name": "1. Bare",
        "changes": "User message only, no instructions beyond 'summarize'",
        "system": None,
        "user": "Summarize this:\n\n{ticket}",
    },
    {
        "name": "2. + Role",
        "changes": "Adds a system prompt giving the model a role",
        "system": "You are an experienced customer-support team lead.",
        "user": "Summarize this:\n\n{ticket}",
    },
    {
        "name": "3. + Clear task & audience",
        "changes": "States the goal and who reads the output",
        "system": "You are an experienced customer-support team lead.",
        "user": "Triage the support ticket below for the on-call support agent, who has 30 seconds to read "
        "your note. Say what happened, how urgent it is, and what the agent should do next.\n\n{ticket}",
    },
    {
        "name": "4. + Context",
        "changes": "Adds the company's shipping policy so next steps can follow it",
        "system": "You are an experienced customer-support team lead.\n\n" + POLICY,
        "user": "Triage the support ticket below for the on-call support agent, who has 30 seconds to read "
        "your note. Say what happened, how urgent it is, and what the agent should do next.\n\n{ticket}",
    },
    {
        "name": "5. + Output template",
        "changes": "Asks for a fixed plain-text layout",
        "system": "You are an experienced customer-support team lead.\n\n" + POLICY,
        "user": "Triage the support ticket below for the on-call support agent.\n\n{ticket}\n\n"
        "Respond in exactly this format:\n" + STRUCTURED_FORMAT,
    },
    {
        "name": "6. + JSON output",
        "changes": "Asks for machine-readable JSON instead of prose",
        "system": "You are an experienced customer-support team lead.\n\n" + POLICY,
        "user": "Triage the support ticket below.\n\n{ticket}\n\n"
        'Respond with only a JSON object: {{"summary": str, "priority": "low"|"medium"|"high"|"urgent", '
        '"next_steps": [str]}}. No markdown, no extra text.',
    },
    {
        "name": "7. + Few-shot example",
        "changes": "Shows one worked example (as a prior conversation turn) before the real ticket",
        "system": "You are an experienced customer-support team lead. Triage tickets for the on-call agent.\n\n" + POLICY,
        "examples": [(FEW_SHOT_TICKET, FEW_SHOT_ANSWER)],
        "user": "{ticket}",
    },
    {
        "name": "8. + Constraints",
        "changes": "Adds limits: length, no invented facts, policy-only actions",
        "system": "You are an experienced customer-support team lead.\n\n" + POLICY,
        "user": "Triage the support ticket below for the on-call support agent.\n\n{ticket}\n\n"
        "Respond in exactly this format:\n" + STRUCTURED_FORMAT + "\n\nRules: at most 60 words total. "
        "Only use facts stated in the ticket or the policy; do not invent dates, amounts or promises. "
        "Every next step must be allowed by the policy.",
    },
    {
        "name": "9. + Reason first",
        "changes": "Asks the model to reason before answering, then give the answer",
        "system": "You are an experienced customer-support team lead.\n\n" + POLICY,
        "user": "Triage the support ticket below for the on-call support agent.\n\n{ticket}\n\n"
        "First, under 'Analysis:', list which policy rules apply to this ticket and why. "
        "Then, under 'Answer:', respond in this format:\n" + STRUCTURED_FORMAT,
    },
    {
        "name": "10. Everything + delimiters",
        "changes": "Combines role, task, context, example, format and constraints; uses XML tags to separate parts",
        "system": "You are an experienced customer-support team lead who writes triage notes for on-call agents. "
        "Agents read your note in 30 seconds, so be precise and brief.\n\n<policy>\n" + POLICY + "\n</policy>\n\n"
        "Rules:\n- Only use facts from the ticket and the policy. Never invent dates, amounts or promises.\n"
        "- Every next step must be allowed by the policy.\n- At most 60 words total.\n\n"
        "<example_ticket>\n" + FEW_SHOT_TICKET + "\n</example_ticket>\n<example_note>\n" + FEW_SHOT_ANSWER + "\n</example_note>",
        "user": "<ticket>\n{ticket}\n</ticket>\n\nWrite the triage note in exactly this format:\n" + STRUCTURED_FORMAT,
    },
]


def build_messages(variant: dict, ticket: str) -> list[dict]:
    messages = [{"role": "system", "content": variant["system"]}] if variant["system"] else []
    for example_in, example_out in variant.get("examples", []):
        messages += [{"role": "user", "content": example_in}, {"role": "assistant", "content": example_out}]
    messages.append({"role": "user", "content": variant["user"].format(ticket=ticket)})
    return messages


def auto_checks(text: str) -> dict:
    """Cheap, objective signals. Your own judgment (in the report) is the real score."""
    lowered = text.lower()
    try:
        json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        valid_json = True
    except ValueError:
        valid_json = False
    return {
        "words": len(text.split()),
        "has priority": any(p in lowered for p in ("urgent", "high", "medium", "low")),
        "mentions order": "ord-10422" in lowered,
        "mentions express refund": "express" in lowered and "refund" in lowered,
        "valid JSON": valid_json,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=CHAT_MODEL)
    parser.add_argument("--only", help="comma-separated variant numbers, e.g. 1,5,10")
    args = parser.parse_args()

    chosen = [VARIANTS[int(n) - 1] for n in args.only.split(",")] if args.only else VARIANTS
    rows = []
    for variant in chosen:
        print(f"running {variant['name']} ...", flush=True)
        result = chat(build_messages(variant, TICKET), model=args.model, temperature=0, seed=42, num_predict=400)
        rows.append((variant, result, auto_checks(result.text)))
        print(f"  {result.prompt_tokens} in / {result.output_tokens} out tokens, {result.seconds:.1f}s")

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    report = out_dir / "comparison.md"
    report.write_text(render_report(rows, args.model), encoding="utf-8")
    print(f"\nwrote {report}")


def render_report(rows, model: str) -> str:
    check_names = list(rows[0][2])
    lines = [
        f"# Prompt variant comparison ({model}, temperature 0, seed 42)",
        "",
        "Fill in **Your score** (1-5) after reading each output. Ask: Is it accurate? Usable by the agent "
        "in 30 seconds? Does it follow policy? Is the format consistent enough to parse?",
        "",
        "| Variant | In tok | Out tok | Sec | " + " | ".join(check_names) + " | Your score |",
        "|---|---:|---:|---:|" + "---|" * len(check_names) + "---|",
    ]
    for variant, result, checks in rows:
        cells = [str(v) if not isinstance(v, bool) else ("yes" if v else "-") for v in checks.values()]
        lines.append(
            f"| {variant['name']} | {result.prompt_tokens} | {result.output_tokens} | {result.seconds:.1f} | "
            + " | ".join(cells) + " |  |"
        )
    lines += ["", "## Ticket used", "", "```", TICKET, "```", ""]
    for variant, result, _ in rows:
        lines += [
            f"## {variant['name']}",
            "",
            f"*Changes:* {variant['changes']}",
            "",
            "```",
            result.text.strip(),
            "```",
            "",
            "*Your notes:* ",
            "",
        ]
    lines += [
        "## Takeaways (write your own)",
        "",
        "- Which single change improved the output the most?",
        "- Which change cost the most tokens for the least gain?",
        "- Which variant would you put in production, and why?",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
