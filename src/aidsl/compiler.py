from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple, Union


@dataclass
class Line:
    number: int
    indent: int
    text: str


class DSLCompileError(ValueError):
    pass


_MACRO_NAMES = {"F", "M", "FM", "S", "A", "E"}
_PLACEHOLDER_RE = re.compile(r"\b_\b")
_LEN_RE = re.compile(r"\blen\(")


def _normalize_lines(source: str) -> List[Line]:
    lines: List[Line] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2 != 0:
            raise DSLCompileError(
                f"Line {number}: indentation must use multiples of 2 spaces"
            )
        lines.append(Line(number=number, indent=indent // 2, text=stripped))
    return lines


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


def _replace_placeholder(expr: str, var_name: str) -> str:
    return _PLACEHOLDER_RE.sub(var_name, expr)


def _translate_len(expr: str, backend: str) -> str:
    if backend == "cpp":
        return re.sub(r"\blen\(", "tl_len(", expr)
    return expr


def _infer_cpp_list_type(items: Sequence[str]) -> str:
    if not items:
        return ""
    if all(item.startswith('"') and item.endswith('"') for item in items):
        return "std::vector<std::string>"
    if all(re.fullmatch(r"-?\d+", item) for item in items):
        return "std::vector<int>"
    return "std::vector"


def _translate_cpp_literal(expr: str) -> str:
    stripped = expr.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return stripped
    inner = stripped[1:-1].strip()
    if not inner:
        return "std::vector<int>{}"
    items = _split_top_level_args(inner)
    rendered = ", ".join(_translate_cpp_literal(item) for item in items)
    vector_type = _infer_cpp_list_type(items)
    if vector_type == "std::vector":
        return f"std::vector{{{rendered}}}"
    return f"{vector_type}{{{rendered}}}"


def _expand_macro(name: str, args: List[str], backend: str) -> str:
    if name == "S":
        if len(args) != 1:
            raise DSLCompileError("S(seq) expects exactly 1 argument")
        if backend == "cpp":
            return f"tl_sum({args[0]})"
        return f"sum({args[0]})"

    if name == "F":
        if len(args) != 2:
            raise DSLCompileError("F(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        if backend == "cpp":
            return (
                f"tl_filter({seq}, [&](const auto& it) {{ "
                f"return {_replace_placeholder(cond, 'it')}; }})"
            )
        return f"[it for it in {seq} if {_replace_placeholder(cond, 'it')}]"

    if name == "M":
        if len(args) != 2:
            raise DSLCompileError("M(seq, expr) expects exactly 2 arguments")
        seq, expr = args
        if backend == "cpp":
            return (
                f"tl_map({seq}, [&](const auto& it) {{ "
                f"return {_replace_placeholder(expr, 'it')}; }})"
            )
        return f"[{_replace_placeholder(expr, 'it')} for it in {seq}]"

    if name == "FM":
        if len(args) != 3:
            raise DSLCompileError("FM(seq, cond, expr) expects exactly 3 arguments")
        seq, cond, expr = args
        if backend == "cpp":
            return (
                f"tl_filter_map({seq}, [&](const auto& it) {{ "
                f"return {_replace_placeholder(cond, 'it')}; }}, "
                f"[&](const auto& it) {{ return {_replace_placeholder(expr, 'it')}; }})"
            )
        return (
            f"[{_replace_placeholder(expr, 'it')} "
            f"for it in {seq} if {_replace_placeholder(cond, 'it')}]"
        )

    if name == "A":
        if len(args) != 2:
            raise DSLCompileError("A(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        if backend == "cpp":
            return (
                f"tl_any({seq}, [&](const auto& it) {{ "
                f"return {_replace_placeholder(cond, 'it')}; }})"
            )
        return f"any({_replace_placeholder(cond, 'it')} for it in {seq})"

    if name == "E":
        if len(args) != 2:
            raise DSLCompileError("E(seq, cond) expects exactly 2 arguments")
        seq, cond = args
        if backend == "cpp":
            return (
                f"tl_all({seq}, [&](const auto& it) {{ "
                f"return {_replace_placeholder(cond, 'it')}; }})"
            )
        return f"all({_replace_placeholder(cond, 'it')} for it in {seq})"

    raise DSLCompileError(f"Unsupported macro `{name}`")


def _rewrite_expression(expr: str, backend: str) -> str:
    out: List[str] = []
    index = 0

    while index < len(expr):
        matched = False
        for name in sorted(_MACRO_NAMES, key=len, reverse=True):
            token = f"{name}("
            if expr.startswith(token, index):
                end = _find_matching_paren(expr, index + len(name))
                raw_args = expr[index + len(token):end]
                args = [
                    _rewrite_expression(arg, backend)
                    for arg in _split_top_level_args(raw_args)
                ]
                out.append(_expand_macro(name, args, backend))
                index = end + 1
                matched = True
                break
        if matched:
            continue
        out.append(expr[index])
        index += 1

    rewritten = "".join(out)
    rewritten = _translate_len(rewritten, backend)
    if backend == "cpp":
        rewritten = _translate_cpp_literal(rewritten)
    return rewritten


def _emit_python_header(kind: str, rest: str) -> str:
    if kind == "f":
        return f"def {rest}:"
    if kind == "?":
        return f"if {rest}:"
    if kind == "w":
        return f"while {rest}:"
    if kind == "for":
        return f"for {rest}:"
    raise AssertionError(f"unsupported header kind: {kind}")


def _compile_python_line(
    text: str, next_indent: int, current_indent: int, line_number: int
) -> str:
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
        return _emit_python_header(head, tail)

    if head == "=":
        name, sep, expr = tail.partition(" ")
        if not sep or not name or not expr:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= name expression`"
            )
        return f"{name} = {_rewrite_expression(expr, 'python')}"

    if head == "r":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `r` requires an expression")
        return f"return {_rewrite_expression(tail, 'python')}"

    if head == "p":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `p` requires an expression")
        return f"print({_rewrite_expression(tail, 'python')})"

    if head == "py":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `py` requires a statement")
        return _rewrite_expression(tail, "python")

    return _rewrite_expression(text, "python")


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
        compiled_line = _compile_python_line(
            text=line.text,
            next_indent=next_indent,
            current_indent=line.indent,
            line_number=line.number,
        )
        compiled.append(("    " * line.indent) + compiled_line)
    return "\n".join(compiled) + "\n"


def _split_top_level_blocks(lines: Sequence[Line]) -> Tuple[List[List[Line]], List[Line]]:
    functions: List[List[Line]] = []
    main_lines: List[Line] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.indent == 0 and line.text.startswith("f "):
            end = index + 1
            while end < len(lines) and lines[end].indent > 0:
                end += 1
            functions.append(lines[index:end])
            index = end
            continue
        main_lines.append(line)
        index += 1
    return functions, main_lines


def _convert_cpp_params(rest: str) -> str:
    name, _, arg_blob = rest.partition("(")
    args = arg_blob[:-1].strip()
    if not args:
        return f"auto {name.strip()}()"
    params = ", ".join(
        f"const auto& {arg.strip()}" for arg in args.split(",") if arg.strip()
    )
    return f"auto {name.strip()}({params})"


def _compile_cpp_statement(text: str, line_number: int) -> str:
    if text == ":":
        return "else"

    parts = text.split(" ", 1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ""

    if head == "f":
        if not tail:
            raise DSLCompileError(f"Line {line_number}: `f` requires content")
        return _convert_cpp_params(tail)
    if head == "?":
        return f"if ({_rewrite_expression(tail, 'cpp')})"
    if head == "w":
        return f"while ({_rewrite_expression(tail, 'cpp')})"
    if head == "for":
        return f"for ({tail})"
    if head == "=":
        name, sep, expr = tail.partition(" ")
        if not sep or not name or not expr:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= name expression`"
            )
        return f"auto {name} = {_rewrite_expression(expr, 'cpp')};"
    if head == "r":
        return f"return {_rewrite_expression(tail, 'cpp')};"
    if head == "p":
        return f"tl_print({_rewrite_expression(tail, 'cpp')});"
    if head == "py":
        return tail
    return _rewrite_expression(text, "cpp") + ";"


def _cpp_requires_block(text: str) -> bool:
    return (
        text == ":"
        or text.startswith("f ")
        or text.startswith("? ")
        or text.startswith("w ")
        or text.startswith("for ")
    )


def _emit_cpp_lines(
    lines: Sequence[Line], start: int, indent: int
) -> Tuple[List[str], int]:
    out: List[str] = []
    index = start

    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise DSLCompileError(
                f"Line {line.number}: indentation jumped more than one level"
            )

        next_indent = lines[index + 1].indent if index + 1 < len(lines) else -1
        has_child = next_indent == indent + 1
        statement = _compile_cpp_statement(line.text, line.number)

        if _cpp_requires_block(line.text):
            if not has_child:
                raise DSLCompileError(
                    f"Line {line.number}: block header must be followed by an indented body"
                )
            out.append(("    " * indent) + statement + " {")
            child_lines, new_index = _emit_cpp_lines(lines, index + 1, indent + 1)
            out.extend(child_lines)
            out.append(("    " * indent) + "}")
            index = new_index
            continue

        out.append(("    " * indent) + statement)
        index += 1

    return out, index


def compile_source_cpp(source: str) -> str:
    lines = _normalize_lines(source)
    function_blocks, main_lines = _split_top_level_blocks(lines)

    rendered: List[str] = [
        "#include <algorithm>",
        "#include <iostream>",
        "#include <numeric>",
        "#include <optional>",
        "#include <string>",
        "#include <utility>",
        "#include <vector>",
        "",
        "template <class T>",
        "auto tl_len(const T& value) {",
        "    return static_cast<int>(value.size());",
        "}",
        "",
        "template <class Seq>",
        "auto tl_sum(const Seq& seq) {",
        "    using Value = typename Seq::value_type;",
        "    return std::accumulate(seq.begin(), seq.end(), Value{});",
        "}",
        "",
        "template <class Seq, class Pred>",
        "auto tl_filter(const Seq& seq, Pred pred) {",
        "    Seq out;",
        "    for (const auto& it : seq) {",
        "        if (pred(it)) {",
        "            out.push_back(it);",
        "        }",
        "    }",
        "    return out;",
        "}",
        "",
        "template <class Seq, class Mapper>",
        "auto tl_map(const Seq& seq, Mapper mapper) {",
        "    using Out = decltype(mapper(*seq.begin()));",
        "    std::vector<Out> out;",
        "    out.reserve(seq.size());",
        "    for (const auto& it : seq) {",
        "        out.push_back(mapper(it));",
        "    }",
        "    return out;",
        "}",
        "",
        "template <class Seq, class Pred, class Mapper>",
        "auto tl_filter_map(const Seq& seq, Pred pred, Mapper mapper) {",
        "    using Out = decltype(mapper(*seq.begin()));",
        "    std::vector<Out> out;",
        "    for (const auto& it : seq) {",
        "        if (pred(it)) {",
        "            out.push_back(mapper(it));",
        "        }",
        "    }",
        "    return out;",
        "}",
        "",
        "template <class Seq, class Pred>",
        "bool tl_any(const Seq& seq, Pred pred) {",
        "    return std::any_of(seq.begin(), seq.end(), pred);",
        "}",
        "",
        "template <class Seq, class Pred>",
        "bool tl_all(const Seq& seq, Pred pred) {",
        "    return std::all_of(seq.begin(), seq.end(), pred);",
        "}",
        "",
        "template <class T>",
        "void tl_print(const T& value) {",
        "    std::cout << value << std::endl;",
        "}",
        "",
        "template <class T>",
        "void tl_print(const std::vector<T>& values) {",
        "    std::cout << \"[\";",
        "    for (std::size_t i = 0; i < values.size(); ++i) {",
        "        if (i != 0) {",
        "            std::cout << \", \";",
        "        }",
        "        std::cout << values[i];",
        "    }",
        "    std::cout << \"]\" << std::endl;",
        "}",
        "",
    ]

    for block in function_blocks:
        body, _ = _emit_cpp_lines(block, 0, 0)
        rendered.extend(body)
        rendered.append("")

    rendered.append("int main() {")
    if main_lines:
        body, _ = _emit_cpp_lines(main_lines, 0, 0)
        for line in body:
            rendered.append("    " + line)
    rendered.append("    return 0;")
    rendered.append("}")
    rendered.append("")
    return "\n".join(rendered)


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


def compile_file(path: Union[str, Path], target: str = "python") -> str:
    source = Path(path).read_text(encoding="utf-8")
    if target == "python":
        return compile_source(source)
    if target == "cpp":
        return compile_source_cpp(source)
    raise DSLCompileError(f"Unsupported target `{target}`")


def run_compiled(source: str, filename: str = "<aidsl>") -> Dict[str, object]:
    compiled = compile_source(source)
    namespace: Dict[str, object] = {}
    exec(compile(compiled, filename, "exec"), namespace, namespace)
    return namespace


def iter_examples(example_dir: Union[str, Path]) -> Iterable[Path]:
    yield from sorted(Path(example_dir).glob("*.aidl"))
