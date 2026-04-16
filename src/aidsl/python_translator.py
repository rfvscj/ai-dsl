from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .frontend import (
    DSLCompileError,
    find_matching_paren,
    normalize_lines,
    split_top_level_args,
    split_top_level_statements,
)
from .rules import load_python_rules

_PYTHON_RULES = load_python_rules()
_MACRO_SPECS = _PYTHON_RULES["macros"]
_MACRO_NAMES = set(_MACRO_SPECS)
_PLACEHOLDER_RE = re.compile(r"\b_\b")
_PLACEHOLDER_KEY_RE = re.compile(r"\b_k\b")
_PLACEHOLDER_VALUE_RE = re.compile(r"\b_v\b")


def _replace_placeholders(
    expr: str,
    item_var: str = "it",
    key_var: str = "k",
    value_var: str = "v",
) -> str:
    expr = _PLACEHOLDER_KEY_RE.sub(key_var, expr)
    expr = _PLACEHOLDER_VALUE_RE.sub(value_var, expr)
    return _PLACEHOLDER_RE.sub(item_var, expr)


def _expand_macro(name: str, args: List[str]) -> str:
    if name == "SEQ":
        return f"nn.Sequential({', '.join(args)})"
    if name == "C2":
        in_channels, out_channels, kernel_size = args
        return f"nn.Conv2d({in_channels}, {out_channels}, kernel_size={kernel_size})"
    if name == "RL":
        return "nn.ReLU()"
    if name == "FL":
        return "nn.Flatten()"
    if name == "LN":
        in_features, out_features = args
        return f"nn.Linear({in_features}, {out_features})"
    if name == "CE":
        return "nn.CrossEntropyLoss()"
    if name == "SGD":
        params, lr = args
        return f"optim.SGD({params}, lr={lr})"
    if name == "DEV":
        return f"torch.device({args[0]})"
    if name == "TR":
        return f"torch.randn({', '.join(args)})"
    if name == "TI":
        return f"torch.randint({', '.join(args)})"
    if name == "ANYN":
        joined = ", ".join(args)
        return f"any(it is None for it in ({joined},))"
    if name == "ALLNN":
        joined = ", ".join(args)
        return f"all(it is not None for it in ({joined},))"
    if name == "CNTNN":
        joined = ", ".join(args)
        return f"sum(1 for it in ({joined},) if it is not None)"
    if name == "CO":
        value, fallback = args
        return f"({value} if {value} is not None else {fallback})"
    if name == "KV":
        obj, key, value = args
        return (
            f"{{{_replace_placeholders(key)}: {_replace_placeholders(value)} "
            f"for k, v in {obj}.items()}}"
        )
    if name == "KVF":
        obj, key, value, cond = args
        return (
            f"{{{_replace_placeholders(key)}: {_replace_placeholders(value)} "
            f"for k, v in {obj}.items() if {_replace_placeholders(cond)}}}"
        )
    if name == "SFM":
        seq, cond, expr = args
        return (
            f"sum({_replace_placeholders(expr)} "
            f"for it in {seq} if {_replace_placeholders(cond)})"
        )
    if name == "CF":
        seq, cond = args
        return f"sum(1 for it in {seq} if {_replace_placeholders(cond)})"
    if name == "DFM":
        seq, key, value, cond = args
        return (
            f"{{{_replace_placeholders(key)}: {_replace_placeholders(value)} "
            f"for it in {seq} if {_replace_placeholders(cond)}}}"
        )
    if name == "S":
        return f"sum({args[0]})"
    if name == "F":
        seq, cond = args
        return f"[it for it in {seq} if {_replace_placeholders(cond)}]"
    if name == "M":
        seq, expr = args
        return f"[{_replace_placeholders(expr)} for it in {seq}]"
    if name == "FM":
        seq, cond, expr = args
        return (
            f"[{_replace_placeholders(expr)} "
            f"for it in {seq} if {_replace_placeholders(cond)}]"
        )
    if name == "A":
        seq, cond = args
        return f"any({_replace_placeholders(cond)} for it in {seq})"
    if name == "E":
        seq, cond = args
        return f"all({_replace_placeholders(cond)} for it in {seq})"
    raise DSLCompileError(f"Unsupported macro `{name}`")


def rewrite_python_expression(expr: str) -> str:
    out: List[str] = []
    index = 0
    while index < len(expr):
        matched = False
        for name in sorted(_MACRO_NAMES, key=len, reverse=True):
            token = f"{name}("
            if expr.startswith(token, index):
                end = find_matching_paren(expr, index + len(name))
                raw_args = expr[index + len(token):end]
                args = [
                    rewrite_python_expression(arg)
                    for arg in split_top_level_args(raw_args)
                ]
                spec = _MACRO_SPECS[name]
                min_arity = spec.get("min_arity")
                expected = spec.get("arity")
                if min_arity is not None:
                    if len(args) < min_arity:
                        raise DSLCompileError(f"{name} expects at least {min_arity} argument")
                elif expected is not None and len(args) != expected:
                    raise DSLCompileError(f"{name} expects exactly {expected} arguments")
                out.append(_expand_macro(name, args))
                index = end + 1
                matched = True
                break
        if matched:
            continue
        out.append(expr[index])
        index += 1
    return "".join(out)


def _emit_header(kind: str, rest: str) -> str:
    if kind == "f":
        return f"def {rest}:"
    if kind == "?":
        return f"if {rest}:"
    if kind == "elif":
        return f"elif {rest}:"
    if kind == "w":
        return f"while {rest}:"
    if kind == "for":
        return f"for {rest}:"
    if kind == "class":
        return f"class {rest}:"
    if kind == "with":
        return f"with {rest}:"
    if kind == "except":
        return f"except {rest}:"
    if kind == "try":
        return "try:"
    if kind == "finally":
        return "finally:"
    raise AssertionError(f"unsupported header kind: {kind}")


def _split_assignment_tail(tail: str) -> Tuple[str, str]:
    depth = 0
    quote = ""
    escape = False
    pairs = {"(": ")", "[": "]", "{": "}"}
    closing = set(pairs.values())
    for index, char in enumerate(tail):
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
        if char == " " and depth == 0:
            return tail[:index], tail[index + 1 :]
    raise DSLCompileError("assignment must separate target and expression with a top-level space")


def _translate_line(text: str, next_indent: int, current_indent: int, line_number: int) -> str:
    if text == ":":
        if next_indent <= current_indent:
            raise DSLCompileError(
                f"Line {line_number}: else block must be followed by an indented body"
            )
        return "else:"
    parts = text.split(" ", 1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    if head in {"f", "?", "elif", "w", "for", "class", "with", "except"}:
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `{head}` requires content")
        if next_indent <= current_indent:
            raise DSLCompileError(
                f"Line {line_number}: block header must be followed by an indented body"
            )
        return _emit_header(head, rewrite_python_expression(tail))
    if head in {"try", "finally"}:
        if tail:
            raise DSLCompileError(f"Line {line_number}: `{head}` does not take inline content")
        if next_indent <= current_indent:
            raise DSLCompileError(
                f"Line {line_number}: block header must be followed by an indented body"
            )
        return _emit_header(head, "")
    if head == "=":
        try:
            name, expr = _split_assignment_tail(tail)
        except DSLCompileError as exc:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= target expression`"
            ) from exc
        if not name or not expr:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= target expression`"
            )
        return f"{name} = {rewrite_python_expression(expr)}"
    if head == "==":
        items = split_top_level_statements(tail)
        if not items:
            raise DSLCompileError(f"Line {line_number}: `==` requires at least one assignment")
        rendered: List[str] = []
        for item in items:
            try:
                name, expr = _split_assignment_tail(item)
            except DSLCompileError as exc:
                raise DSLCompileError(
                    f"Line {line_number}: grouped assignment entries must look like `target expression`"
                ) from exc
            rendered.append(f"{name} = {rewrite_python_expression(expr)}")
        return "\n".join(rendered)
    if head == ">>":
        items = split_top_level_statements(tail)
        if not items:
            raise DSLCompileError(f"Line {line_number}: `>>` requires at least one statement")
        return "\n".join(rewrite_python_expression(item) for item in items)
    if head == "r":
        if not tail:
            return "return"
        return f"return {rewrite_python_expression(tail)}"
    if head == "p":
        return f"print({rewrite_python_expression(tail)})"
    if head == "py":
        return rewrite_python_expression(tail)
    return rewrite_python_expression(text)


def translate_source_python(source: str) -> str:
    raw_lines = source.splitlines()
    if raw_lines and raw_lines[0].strip() == "py" and raw_lines[0].strip() == raw_lines[0]:
        passthrough = "\n".join(raw_lines[1:])
        return passthrough + ("\n" if passthrough and not passthrough.endswith("\n") else "")
    lines = normalize_lines(source)
    if not lines:
        return ""
    out: List[str] = []
    for index, line in enumerate(lines):
        next_indent = lines[index + 1].indent if index + 1 < len(lines) else -1
        if index > 0 and line.indent > lines[index - 1].indent + 1:
            raise DSLCompileError(
                f"Line {line.number}: indentation jumped more than one level"
            )
        translated = _translate_line(line.text, next_indent, line.indent, line.number)
        indent = "    " * line.indent
        for rendered_line in translated.splitlines():
            out.append(indent + rendered_line)
    return "\n".join(out) + "\n"


def run_translated_python(source: str, filename: str = "<aidsl>") -> Dict[str, object]:
    translated = translate_source_python(source)
    namespace: Dict[str, object] = {}
    exec(compile(translated, filename, "exec"), namespace, namespace)
    return namespace
