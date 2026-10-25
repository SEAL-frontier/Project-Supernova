"""Local, numerical-only chat math. No evaluation of Python source."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from io import BytesIO
import math
import operator
import re
import threading
import time


MAX_EXPRESSION_CHARS = 512
MAX_AST_NODES = 128
MAX_EXPRESSION_DEPTH = 20
MAX_EXPONENT = 100
MAX_MAGNITUDE = 1e100
CALCULATE_TIMEOUT_SECONDS = 0.05


class MathInputError(ValueError):
    """Stable, safe-to-report error code, never a user expression or traceback."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise MathInputError("math_timeout")


def _number(value: int | float) -> int | float:
    if (type(value) not in (int, float) or abs(value) > MAX_MAGNITUDE
            or (type(value) is float and not math.isfinite(value))):
        raise MathInputError("number_out_of_range")
    return value


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTS = {"pi": math.pi, "e": math.e}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "sin": math.sin, "cos": math.cos,
    "log": math.log, "log10": math.log10, "exp": math.exp, "round": round,
}


def calculate(expression: str) -> int | float:
    """Evaluate bounded real arithmetic using Python precedence, never eval/exec.

    Supports + - * / // % **, unary signs, pi/e, and the explicitly listed
    functions. IEEE-754 floating-point is intentional (not symbolic/financial
    arithmetic). Invalid, unsafe and out-of-budget input raises MathInputError.
    """
    deadline = time.monotonic() + CALCULATE_TIMEOUT_SECONDS
    if (not isinstance(expression, str) or not expression.strip()
            or len(expression) > MAX_EXPRESSION_CHARS):
        raise MathInputError("invalid_expression")
    if not re.fullmatch(r"[A-Za-z0-9_+*/%()., \t-]+", expression):
        raise MathInputError("unsupported_expression")
    nesting = 0
    for char in expression:
        if char == "(":
            nesting += 1
            if nesting > MAX_EXPRESSION_DEPTH:
                raise MathInputError("expression_too_deep")
        elif char == ")":
            nesting -= 1
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise MathInputError("invalid_expression") from None
    pending = [(tree.body, 1)]
    count = 0
    while pending:
        _check_deadline(deadline)
        node, depth = pending.pop()
        count += 1
        if depth > MAX_EXPRESSION_DEPTH or count > MAX_AST_NODES:
            raise MathInputError("expression_too_complex")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    def visit(node):
        _check_deadline(deadline)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return _number(node.value)
        if isinstance(node, ast.Name) and node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _number(_UNARY[type(node.op)](visit(node.operand)))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > MAX_EXPONENT:
                    raise MathInputError("exponent_out_of_range")
                if left and right * math.log10(abs(left)) > 100.000000000001:
                    raise MathInputError("number_out_of_range")
            return _number(_BINARY[type(node.op)](left, right))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCTIONS and not node.keywords):
            name = node.func.id
            arity = (1, 2) if name in ("round", "log") else (1,)
            if len(node.args) not in arity:
                raise MathInputError("invalid_arguments")
            args = [visit(arg) for arg in node.args]
            if name == "round" and len(args) == 2:
                if type(args[1]) is not int or not -15 <= args[1] <= 15:
                    raise MathInputError("invalid_arguments")
            return _number(_FUNCTIONS[name](*args))
        raise MathInputError("unsupported_expression")

    try:
        result = visit(tree.body)
        _check_deadline(deadline)
        return result
    except MathInputError:
        raise
    except (ArithmeticError, TypeError, ValueError):
        raise MathInputError("arithmetic_error") from None


MAX_FORMULA_CHARS = 512
MAX_FORMULA_DEPTH = 12
MAX_FORMULA_COMMANDS = 64
_ALLOWED_COMMANDS = frozenset({
    "frac", "sqrt", "sum", "pi", "sigma", "mu", "exp", "left", "right",
    "pm", "alpha", "beta", "gamma", "quad", "Delta", "approx", "theta",
    "cdot", "omega", "int", "infty", ",", "sin", "cos", "log", "leq",
    "times", "geq", "mathrm", " ",
})


def _formula_source(formula: str) -> str:
    if (not isinstance(formula, str) or not formula.strip()
            or len(formula) > MAX_FORMULA_CHARS):
        raise MathInputError("invalid_formula")
    source = formula.strip()
    for left, right in (("$$", "$$"), ("$", "$"), (r"\(", r"\)"),
                        (r"\[", r"\]")):
        if source.startswith(left) and source.endswith(right):
            source = source[len(left):-len(right)].strip()
            break
    if not source or not re.fullmatch(r"[A-Za-z0-9+*/=^_{}()[\].,| :;<>!\\-]+", source):
        raise MathInputError("unsupported_formula")
    commands = re.findall(r"\\([A-Za-z]+|[^A-Za-z])", source)
    if len(commands) > MAX_FORMULA_COMMANDS:
        raise MathInputError("formula_too_complex")
    # Literal ASCII labels only: never interpret nested TeX or rewrite equations.
    # MathText drops bare spaces in math mode, so preserve label word boundaries.
    source = re.sub(r"\\text\{([A-Za-z0-9 +.,-]+)\}",
                    lambda match: r"\mathrm{" + match[1].replace(" ", r"\ ") + "}",
                    source)
    commands = re.findall(r"\\([A-Za-z]+|[^A-Za-z])", source)
    if len(commands) > MAX_FORMULA_COMMANDS:
        raise MathInputError("formula_too_complex")
    if any(command not in _ALLOWED_COMMANDS for command in commands):
        raise MathInputError("unsupported_formula")
    depth = 0
    for char in source:
        if char == "{":
            depth += 1
            if depth > MAX_FORMULA_DEPTH:
                raise MathInputError("formula_too_deep")
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise MathInputError("invalid_formula")
    if depth:
        raise MathInputError("invalid_formula")
    return source


MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 480
MAX_IMAGE_PIXELS = 768000
MAX_PNG_BYTES = 256000
RENDER_TIMEOUT_SECONDS = 5.0
_RENDER_LOCK = threading.Lock()
_DPI = 120
_FONT_SIZE = 22
_PADDING = 12


@dataclass(frozen=True)
class FormulaImage:
    """In-memory attachment; never a URL, file path or a delivery receipt."""

    png: bytes
    width: int
    height: int
    font_size: float = _FONT_SIZE
    media_type: str = "image/png"
    filename: str = "formula.png"


def render_formula(formula: str) -> FormulaImage:
    """Render one bounded MathText expression in memory, not external TeX.

    Fixed 22pt type: oversized equations fail instead of producing illegible
    thumbnails. The deadline includes lock wait and cold imports. It is
    cooperative: it checks between bounded parser/draw operations, not a hard
    interrupt of native code. There is deliberately no worker/thread/process.
    """
    deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
    source = _formula_source(formula)
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not _RENDER_LOCK.acquire(timeout=remaining):
        raise MathInputError("math_timeout")
    figure = None
    try:
        _check_deadline(deadline)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from matplotlib.font_manager import FontProperties
        from matplotlib.mathtext import MathTextParser
        _check_deadline(deadline)

        expression = "$" + source + "$"
        font = FontProperties(family="DejaVu Sans", size=_FONT_SIZE,
                              math_fontfamily="dejavusans")
        measured = MathTextParser("path").parse(expression, dpi=_DPI, prop=font)
        _check_deadline(deadline)
        width = max(32, math.ceil(measured.width) + 2 * _PADDING)
        height = max(32, math.ceil(measured.height) + 2 * _PADDING)
        if (width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT
                or width * height > MAX_IMAGE_PIXELS):
            raise MathInputError("formula_too_large")
        figure = Figure(figsize=(width / _DPI, height / _DPI), dpi=_DPI,
                        facecolor="white", edgecolor="white", layout="none")
        canvas = FigureCanvasAgg(figure)
        figure.text(_PADDING / width, (_PADDING + measured.depth) / height,
                    expression, fontproperties=font, color="black",
                    ha="left", va="baseline", usetex=False, parse_math=True)
        with BytesIO() as output:
            canvas.print_png(output, metadata={"Software": "Kei MathText"})
            _check_deadline(deadline)
            if output.tell() > MAX_PNG_BYTES:
                raise MathInputError("formula_too_large")
            return FormulaImage(output.getvalue(), width, height)
    except MathInputError:
        raise
    except ImportError:
        raise MathInputError("renderer_unavailable") from None
    except (ValueError, RuntimeError, RecursionError, OverflowError):
        raise MathInputError("unsupported_formula") from None
    finally:
        if figure is not None:
            figure.clear()
        _RENDER_LOCK.release()


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Bounded real-number calculator. Use plain-text answers by default. "
                "Operators + - * / // % **; pi, e; sqrt, abs, sin, cos, log, "
                "log10, exp, round. No variables or Python code."
            ),
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "maxLength": 512}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_formula",
            "description": (
                "Prepare a formula PNG only when typesetting is helpful/requested. "
                "MathText fractions/roots/sums/integrals, basic Greek and operators; "
                "not full LaTeX. No raw LaTeX in final chat. No delivery implied."
            ),
            "parameters": {
                "type": "object",
                "properties": {"formula": {"type": "string", "maxLength": 512}},
                "required": ["formula"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass(frozen=True)
class ToolResult:
    """JSON model content and an optional binary attachment on separate channels."""

    ok: bool
    content: dict
    attachment: FormulaImage | None = None


def handle_tool(name: str, arguments: dict) -> ToolResult:
    """Handle already-decoded tool arguments synchronously, with no I/O effects."""
    if name not in ("calculate", "render_formula"):
        return ToolResult(False, {"ok": False, "error": "unknown_math_tool"})
    field = "expression" if name == "calculate" else "formula"
    if not isinstance(arguments, dict) or set(arguments) != {field}:
        return ToolResult(False, {"ok": False, "error": "invalid_arguments"})
    try:
        if name == "calculate":
            value = calculate(arguments[field])
            text = (str(int(value)) if isinstance(value, float) and value.is_integer()
                    and abs(value) < 1e15 else str(value))
            return ToolResult(True, {"ok": True, "value": value, "text": text})
        image = render_formula(arguments[field])
        return ToolResult(True, {
            "ok": True,
            "text": "Formula image prepared.",
            "image": {"filename": image.filename, "media_type": image.media_type,
                      "width": image.width, "height": image.height,
                      "bytes": len(image.png)},
        }, image)
    except MathInputError as exc:
        return ToolResult(False, {"ok": False, "error": exc.code})
