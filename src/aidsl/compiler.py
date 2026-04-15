from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Union


@dataclass
class Line:
    number: int
    indent: int
    text: str


class DSLCompileError(ValueError):
    pass


_MACRO_NAMES = {"F", "M", "FM", "S", "A", "E"}
_PLACEHOLDER_RE = re.compile(r"\b_\b")


def _normalize_lines(source: str) -> List[Line]:
    lines: List[Line] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2 != 0:
            raise DSLCompileError(
                f"Line {number}: indentation must use multiples of 2 spaces"
            )
        lines.append(Line(number=number, indent=indent // 2, text=stripped))
    return lines


def _emit_header(kind: str, rest: str) -> str:
    if kind == "f":
        return f"def {rest}:"
    if kind == "?":
        return f"if {rest}:"
    if kind == "w":
        return f"while {rest}:"
    if kind == "for":
        return f"for {rest}:"
    raise AssertionError(f"unsupported header kind: {kind}")


def _find_matching_paren(text: str, start: int) -> int:
    depth = 0
    quote = ""
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    raise DSLCompileError("Unclosed macro call")


def _split_top_level_args(text: str) -> List[str]:
    args: List[str] = []
    start = 0
    depth = 0
    quote = ""
    escape = False
    pairs = {"(": ")", "[": "]", "{": "}"}
    closing = set(pairs.values())

    for index, char in enumerate(text):
        if quote:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in pairs:
            depth += 1
            continue
        if char in closing:
            depth -= 1
            continue
        if char == "," and depth == 0:
            args.append(text[start:index].strip())
            start = index + 1
    args.append(text[start:].strip())
    return args


def _replace_placeholder(expr: str, var_name: str) -> str:
    return _PLACEHOLDER_RE.sub(var_name, expr)


def _expand_macro(name: str, args: List[str]) -> str:
    if name == "S":
        if len(args) != 1:
            raise DSLCompileError("S(seq) expects exactly 1 argument")
        return f"sum({args[0]})"

    if name == "F":
        if len(args) != 2:
            raise DSLCompileError("F(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        return f"[it for it in {seq} if {_replace_placeholder(cond, 'it')}]"

    if name == "M":
        if len(args) != 2:
            raise DSLCompileError("M(seq, expr) expects exactly 2 arguments")
        seq, expr = args
        return f"[{_replace_placeholder(expr, 'it')} for it in {seq}]"

    if name == "FM":
        if len(args) != 3:
            raise DSLCompileError("FM(seq, cond, expr) expects exactly 3 arguments")
        seq, cond, expr = args
        return (
            f"[{_replace_placeholder(expr, 'it')} "
            f"for it in {seq} if {_replace_placeholder(cond, 'it')}]"
        )

    if name == "A":
        if len(args) != 2:
            raise DSLCompileError("A(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        return f"any({_replace_placeholder(cond, 'it')} for it in {seq})"

    if name == "E":
        if len(args) != 2:
            raise DSLCompileError("E(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        return f"all({_replace_placeholder(cond, 'it')} for it in {seq})"

    raise DSLCompileError(f"Unsupported macro `{name}`")


def _rewrite_expression(expr: str) -> str:
    out: List[str] = []
    index = 0

    while index < len(expr):
        matched = False
        for name in sorted(_MACRO_NAMES, key=len, reverse=True):
            token = f"{name}("
            if expr.startswith(token, index):
                end = _find_matching_paren(expr, index + len(name))
                raw_args = expr[index + len(token):end]
                args = [_rewrite_expression(arg) for arg in _split_top_level_args(raw_args)]
                out.append(_expand_macro(name, args))
                index = end + 1
                matched = True
                break
        if matched:
            continue
        out.append(expr[index])
        index += 1

    return "".join(out)


def _compile_line(text: str, next_indent: int, current_indent: int, line_number: int) -> str:
    if text == ":":
        if next_indent <= current_indent:
            raise DSLCompileError(
                f"Line {line_number}: else block must be followed by an indented body"
            )
        return "else:"

    parts = text.split(" ", 1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ""

    if head in {"f", "?", "w", "for"}:
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `{head}` requires content")
        if next_indent <= current_indent:
            raise DSLCompileError(
                f"Line {line_number}: block header must be followed by an indented body"
            )
        return _emit_header(head, tail)

    if head == "=":
        name, sep, expr = tail.partition(" ")
        if not sep or not name or not expr:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= name expression`"
            )
        return f"{name} = {_rewrite_expression(expr)}"

    if head == "r":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `r` requires an expression")
        return f"return {_rewrite_expression(tail)}"

    if head == "p":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `p` requires an expression")
        return f"print({_rewrite_expression(tail)})"

    if head == "py":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `py` requires a statement")
        return _rewrite_expression(tail)

    # Fallback: allow raw expression statements for quick experimentation.
    return _rewrite_expression(text)


def compile_source(source: str) -> str:
    lines = _normalize_lines(source)
    if not lines:
        return ""

    compiled: List[str] = []
    for index, line in enumerate(lines):
        next_indent = lines[index + 1].indent if index + 1 < len(lines) else -1
        if index > 0:
            prev_indent = lines[index - 1].indent
            if line.indent > prev_indent + 1:
                raise DSLCompileError(
                    f"Line {line.number}: indentation jumped more than one level"
                )
        compiled_line = _compile_line(
            text=line.text,
            next_indent=next_indent,
            current_indent=line.indent,
            line_number=line.number,
        )
        compiled.append(("    " * line.indent) + compiled_line)
    return "\n".join(compiled) + "\n"


def count_stats(source: str, compiled: str) -> Dict[str, int]:
    dsl_chars = len(source)
    py_chars = len(compiled)
    dsl_nonempty_lines = len([line for line in source.splitlines() if line.strip()])
    py_nonempty_lines = len([line for line in compiled.splitlines() if line.strip()])
    return {
        "dsl_chars": dsl_chars,
        "python_chars": py_chars,
        "char_delta": py_chars - dsl_chars,
        "dsl_nonempty_lines": dsl_nonempty_lines,
        "python_nonempty_lines": py_nonempty_lines,
    }


def compile_file(path: Union[str, Path]) -> str:
    return compile_source(Path(path).read_text(encoding="utf-8"))


def run_compiled(source: str, filename: str = "<aidsl>") -> Dict[str, object]:
    compiled = compile_source(source)
    namespace: Dict[str, object] = {}
    exec(compile(compiled, filename, "exec"), namespace, namespace)
    return namespace


def iter_examples(example_dir: Union[str, Path]) -> Iterable[Path]:
    yield from sorted(Path(example_dir).glob("*.aidl"))
