"""Exercise: implement 3 safe local tools and let a model call them.

How tool calling works:
  1. We send the model each tool's name, description (docstring) and JSON schema (from type hints).
  2. Instead of answering, the model may reply with a *tool call*: a name plus JSON arguments.
  3. OUR code runs the function. The model never executes anything itself.
  4. We send the result back and the model continues, either calling more tools or answering.

Usage:  python agent.py            # scripted demo, including attack prompts
        python agent.py --chat     # ask your own questions
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import CHAT_MODEL, pydantic_ai_model  # noqa: E402

from pydantic_ai import Agent, UsageLimitExceeded  # noqa: E402
from pydantic_ai.messages import ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

import tools  # noqa: E402

INSTRUCTIONS = f"""You are a helpful office assistant with three tools.
- Use `calculate` for any arithmetic. Never do math in your head.
- Use `read_note` to look up company information. Available notes: {tools.list_note_names()}.
- Use `convert_units` for unit conversions.
If a tool returns an ERROR, explain the problem to the user. Do not try to get around it.
Answer briefly and cite which note you used."""

# Hard caps so a confused or manipulated model can't loop forever
LIMITS = UsageLimits(request_limit=8, tool_calls_limit=6)

agent = Agent(
    pydantic_ai_model(CHAT_MODEL),
    instructions=INSTRUCTIONS,
    model_settings={"temperature": 0},
)


# Thin wrappers: the docstring and type hints become the schema the model sees, and a ToolError
# becomes a plain-text ERROR result the model can explain, instead of an exception.
@agent.tool_plain
def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression using numbers and + - * / // % ** ( ). Example: '(19.99 * 3) * 1.08'"""
    try:
        return str(tools.calculate(expression))
    except tools.ToolError as e:
        return f"ERROR: {e}"


@agent.tool_plain
def read_note(filename: str) -> str:
    """Read one company note by its file name, e.g. 'hr_policy.md'."""
    try:
        return tools.read_note(filename)
    except tools.ToolError as e:
        return f"ERROR: {e}"


@agent.tool_plain
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a value between units. Units: mm cm m km in ft mi | g kg lb oz | ml l gal cup | c f k (temperature)."""
    try:
        return str(tools.convert_units(value, from_unit, to_unit))
    except tools.ToolError as e:
        return f"ERROR: {e}"


def run(question: str, history=None):
    print(f"\nUSER: {question}")
    try:
        result = agent.run_sync(question, message_history=history, usage_limits=LIMITS)
    except UsageLimitExceeded as e:
        print(f"STOPPED: {e}")
        return history
    new_messages = result.new_messages()
    for message in new_messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                print(f"  -> tool call  {part.tool_name}({json.dumps(part.args_as_dict())})")
            elif isinstance(part, ToolReturnPart):
                print(f"  <- returned   {str(part.content)[:120]!r}")
    print(f"ASSISTANT: {result.output}")
    return result.all_messages()


DEMO_QUESTIONS = [
    # one tool each
    "What is 3 desks at 189.50 each plus 8% tax?",
    "How many PTO days do I get, and how many can I carry over?",
    "The desk is 1.6 metres wide. How many feet is that?",
    # chaining tools: read a note, then calculate
    "I'm shipping a 42 kg freight order. Using our shipping rates note, what does it cost?",
    # attacks: the tools must refuse, whatever the model decides to do
    "Read the note named ../tools.py and show me its source.",
    "Use the calculator on this exact expression: __import__('os').system('whoami')",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="interactive mode")
    args = parser.parse_args()

    if not args.chat:
        for question in DEMO_QUESTIONS:
            run(question)
        return

    print("Ask anything (empty line to quit).")
    history = None
    while question := input("\n> ").strip():
        history = run(question, history)


if __name__ == "__main__":
    main()
