"""Three safe local tools. Plain Python with no LLM involved, so each can be unit-tested on its own.

What "safe" means here:
- No shell, no eval/exec, no network, no writes. Each tool is read-only or pure.
- Every argument the model sends is treated as untrusted input and validated.
- Bounded work: input length, number size and file size are all capped.
- Failures raise ToolError with a message the model can act on. They never return a stack trace.
"""
import ast
import operator
from pathlib import Path

NOTES_DIR = Path(__file__).parent / "sandbox" / "notes"


class ToolError(ValueError):
    """A safe, model-readable reason a tool refused or failed."""


# ---------- 1. Calculator: arithmetic only, via a whitelisted AST walk (never eval) ----------

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_EXPRESSION_CHARS = 200
MAX_ABS_VALUE = 1e15
MAX_EXPONENT = 100


def calculate(expression: str) -> float:
    """Evaluate an arithmetic expression like '(19.99 * 3) * 1.08'."""
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ToolError(f"expression longer than {MAX_EXPRESSION_CHARS} characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ToolError(f"not a valid arithmetic expression: {expression!r}") from None
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return _bounded(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise ToolError(f"exponent larger than {MAX_EXPONENT}")
        try:
            return _bounded(_BIN_OPS[type(node.op)](left, right))
        except ZeroDivisionError:
            raise ToolError("division by zero") from None
    # Names, calls, attributes, subscripts, strings, lambdas... are all rejected here
    raise ToolError(f"only numbers and + - * / // % ** ( ) are allowed, found {type(node).__name__}")


def _bounded(value: float) -> float:
    if isinstance(value, complex) or abs(value) > MAX_ABS_VALUE:
        raise ToolError(f"result out of range (limit {MAX_ABS_VALUE:g})")
    return value


# ---------- 2. Note reader: read-only access to one folder, nothing else ----------

ALLOWED_SUFFIXES = {".md", ".txt"}
MAX_FILE_BYTES = 20_000


def list_note_names() -> list[str]:
    return sorted(p.name for p in NOTES_DIR.iterdir() if p.is_file() and p.suffix in ALLOWED_SUFFIXES)


def read_note(filename: str) -> str:
    """Return the text of one note from the sandbox folder."""
    root = NOTES_DIR.resolve()
    # resolve() collapses '..' and follows symlinks, so the containment check sees the real target
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or path.parent != root:
        raise ToolError(f"access denied: {filename!r} is outside the notes folder")
    if path.suffix not in ALLOWED_SUFFIXES:
        raise ToolError(f"only {sorted(ALLOWED_SUFFIXES)} files can be read")
    if not path.is_file():
        raise ToolError(f"no note named {filename!r}. Available notes: {list_note_names()}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ToolError(f"note is larger than {MAX_FILE_BYTES} bytes")
    return path.read_text(encoding="utf-8")


# ---------- 3. Unit converter: table-driven, no free-form input ----------

# factor to convert 1 unit into the base unit of its dimension (metre, kilogram, litre)
_LINEAR_UNITS = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "mi": 1609.344},
    "mass": {"g": 0.001, "kg": 1.0, "lb": 0.45359237, "oz": 0.028349523125},
    "volume": {"ml": 0.001, "l": 1.0, "gal": 3.785411784, "cup": 0.2365882365},
}
_TEMPERATURE_UNITS = {"c", "f", "k"}


def supported_units() -> list[str]:
    return sorted({u for table in _LINEAR_UNITS.values() for u in table} | _TEMPERATURE_UNITS)


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value between units of the same dimension (length, mass, volume, temperature)."""
    src, dst = from_unit.strip().lower(), to_unit.strip().lower()
    if abs(value) > MAX_ABS_VALUE:
        raise ToolError("value out of range")
    if src in _TEMPERATURE_UNITS and dst in _TEMPERATURE_UNITS:
        kelvin = {"c": value + 273.15, "f": (value - 32) * 5 / 9 + 273.15, "k": value}[src]
        if kelvin < 0:
            raise ToolError("temperature below absolute zero")
        return round({"c": kelvin - 273.15, "f": (kelvin - 273.15) * 9 / 5 + 32, "k": kelvin}[dst], 6)
    for table in _LINEAR_UNITS.values():
        if src in table and dst in table:
            return round(value * table[src] / table[dst], 6)
    raise ToolError(f"cannot convert {from_unit!r} to {to_unit!r}. Supported units: {supported_units()}")
