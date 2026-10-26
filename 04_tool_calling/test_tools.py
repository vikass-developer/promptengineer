"""Safety tests for tools.py. These run without an LLM:  python -m pytest -q"""
import pytest

from tools import NOTES_DIR, ToolError, calculate, convert_units, read_note


class TestCalculate:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [("2 + 3", 5), ("(19.99 * 3) * 1.08", pytest.approx(64.7676)), ("-2 ** 2", -4), ("7 // 2 + 7 % 2", 4)],
    )
    def test_arithmetic(self, expression, expected):
        assert calculate(expression) == expected

    @pytest.mark.parametrize(
        "attack",
        [
            "__import__('os').system('dir')",  # function call
            "open('secrets.txt').read()",  # file access
            "().__class__.__bases__[0]",  # attribute walk to escape a sandbox
            "x + 1",  # names / variables
            "'a' * 10",  # strings
            "lambda: 1",
            "[1, 2, 3]",
        ],
    )
    def test_rejects_code(self, attack):
        with pytest.raises(ToolError):
            calculate(attack)

    @pytest.mark.parametrize("expensive", ["9 ** 9 ** 9", "2 ** 1000", "10 ** 20", "1" * 300])
    def test_rejects_unbounded_work(self, expensive):
        with pytest.raises(ToolError):
            calculate(expensive)

    def test_division_by_zero_is_a_tool_error(self):
        with pytest.raises(ToolError, match="division by zero"):
            calculate("1 / 0")


class TestReadNote:
    def test_reads_a_note(self):
        assert "PTO" in read_note("hr_policy.md")

    @pytest.mark.parametrize(
        "attack",
        [
            "../tools.py",
            "..\\tools.py",
            "../../llm.py",
            str(NOTES_DIR.parents[2] / "llm.py"),  # absolute path
            "C:\\Windows\\win.ini",
            "/etc/passwd",
            "subdir/../../tools.py",
        ],
    )
    def test_blocks_path_traversal(self, attack):
        with pytest.raises(ToolError, match="access denied|only"):
            read_note(attack)

    def test_missing_note_lists_alternatives(self):
        with pytest.raises(ToolError, match="Available notes"):
            read_note("nope.md")

    def test_rejects_other_file_types(self):
        with pytest.raises(ToolError, match="only"):
            read_note("script.py")


class TestConvertUnits:
    @pytest.mark.parametrize(
        ("value", "src", "dst", "expected"),
        [(1, "mi", "km", 1.609344), (100, "C", "F", 212), (32, "f", "c", 0), (2, "lb", "kg", 0.907185), (1, "gal", "l", 3.785412)],
    )
    def test_conversions(self, value, src, dst, expected):
        assert convert_units(value, src, dst) == pytest.approx(expected)

    def test_rejects_mixed_dimensions(self):
        with pytest.raises(ToolError, match="cannot convert"):
            convert_units(5, "kg", "km")

    def test_rejects_below_absolute_zero(self):
        with pytest.raises(ToolError, match="absolute zero"):
            convert_units(-500, "c", "k")
