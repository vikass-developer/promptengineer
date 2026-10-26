"""Exercise: build validated Pydantic AI responses.

The model must return a `TicketTriage` object. Pydantic checks the shape (types, enums, lengths,
regex), and an output validator checks meaning (the order ID must really appear in the ticket).
Either failure is sent back to the model as feedback and it gets another attempt.

Usage:  python triage.py [--mode native|tool|prompted] [--model llama3.2:3b]
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import CHAT_MODEL, pydantic_ai_model  # noqa: E402

from pydantic import BaseModel, Field, field_validator  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext, UnexpectedModelBehavior  # noqa: E402
from pydantic_ai.messages import RetryFeedbackPart, RetryPromptPart  # noqa: E402
from pydantic_ai.output import NativeOutput, PromptedOutput, ToolOutput  # noqa: E402


class TicketTriage(BaseModel):
    """Structured triage of one customer-support ticket."""

    category: Literal["billing", "shipping", "technical", "account", "other"]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: Literal["positive", "neutral", "negative"]
    # Required-but-nullable on purpose. With a default (= None) the field drops out of the schema's
    # "required" list, and constrained decoding lets the model skip it entirely, no matter how often
    # the validator asks for it. Try adding a default and watch ticket 4 fail.
    order_id: str | None = Field(
        pattern=r"^ORD-\d{5}$",
        description="Order ID exactly as written in the ticket, e.g. ORD-10422. null if the ticket has none.",
    )
    summary: str = Field(min_length=15, max_length=200, description="One sentence for the support agent.")
    next_steps: list[str] = Field(min_length=1, max_length=4, description="Concrete actions, most important first.")

    @field_validator("next_steps")
    @classmethod
    def steps_are_actions(cls, steps: list[str]) -> list[str]:
        too_short = [s for s in steps if len(s.split()) < 2]
        if too_short:
            raise ValueError(f"each step must be a short action phrase, got {too_short}")
        return steps


INSTRUCTIONS = """You triage customer-support tickets.
Pick the category and priority from the allowed values only.
priority: urgent = customer blocked or threatening to leave; high = money or a missed promise involved;
medium = needs action but not time-critical; low = question or feedback.
Copy the order ID exactly if one appears, otherwise use null. Never invent an order ID."""

OUTPUT_MODES = {
    # Ollama constrains generation to the JSON schema (OpenAI-style response_format)
    "native": NativeOutput(TicketTriage),
    # The model "calls" a final_result tool whose arguments are the object
    "tool": ToolOutput(TicketTriage),
    # The schema goes into the prompt and the model is asked to reply with JSON
    "prompted": PromptedOutput(TicketTriage),
}


def build_agent(model_name: str, mode: str) -> Agent[str, TicketTriage]:
    agent = Agent(
        pydantic_ai_model(model_name),
        deps_type=str,  # the raw ticket text, so the validator can check facts against it
        output_type=OUTPUT_MODES[mode],
        instructions=INSTRUCTIONS,
        model_settings={"temperature": 0},
        retries=3,
    )

    @agent.output_validator
    def grounded_in_ticket(ctx: RunContext[str], triage: TicketTriage) -> TicketTriage:
        """Schema validation can't catch made-up facts. This checks them against the source."""
        if triage.order_id and triage.order_id not in ctx.deps:
            raise ModelRetry(f"order_id {triage.order_id!r} does not appear in the ticket. Use null or the exact ID.")
        if not triage.order_id and re.search(r"ORD-\d{5}", ctx.deps):
            raise ModelRetry("The ticket contains an order ID but order_id is null. Copy it exactly.")
        return triage

    return agent


TICKETS = [
    "Order ORD-10422 was supposed to arrive Friday with express shipping. Tracking hasn't moved in 6 days. "
    "If it's not here by Monday I'm cancelling.",
    "Hi! Just wanted to say the new dashboard is great, much faster than before. Keep it up.",
    "I was charged twice this month for my subscription. Please refund one of them.",
    "The app crashes every time I open Settings on Android 15. Reinstalled twice, same thing. Order ORD-55120 "
    "was the hardware bundle if that matters.",
    "can't log in. password reset email never arrives. tried 4 times. i have a client demo in 1 hour!!!",
]


def count_retries(result) -> int:
    return sum(isinstance(p, RetryPromptPart | RetryFeedbackPart) for m in result.all_messages() for p in m.parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=OUTPUT_MODES, default="native")
    parser.add_argument("--model", default=CHAT_MODEL)
    args = parser.parse_args()

    agent = build_agent(args.model, args.mode)
    passed = 0
    for i, ticket in enumerate(TICKETS, 1):
        print(f"\n--- ticket {i}: {ticket[:70]}...")
        try:
            result = agent.run_sync(f"Triage this ticket:\n\n{ticket}", deps=ticket)
        except UnexpectedModelBehavior as e:
            print(f"FAILED after retries: {e}\n  last error: {e.__cause__}")
            continue
        passed += 1
        triage = result.output
        print(f"OK (retries: {count_retries(result)}, tokens: {result.usage.input_tokens} in / {result.usage.output_tokens} out)")
        print(triage.model_dump_json(indent=2))

    print(f"\n{passed}/{len(TICKETS)} tickets produced a valid TicketTriage (mode={args.mode}, model={args.model})")


if __name__ == "__main__":
    main()
