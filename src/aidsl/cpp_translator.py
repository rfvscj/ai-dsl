from __future__ import annotations

import re
from typing import List, Sequence, Set, Tuple

from .frontend import (
    DSLCompileError,
    Line,
    find_matching_paren,
    normalize_lines,
    split_top_level_args,
    split_top_level_blocks,
)

_MACRO_NAMES = {"SFM", "CF", "F", "M", "FM", "S", "A", "E"}
_PLACEHOLDER_RE = re.compile(r"\b_\b")


def _replace_placeholder(expr: str, var_name: str) -> str:
    return _PLACEHOLDER_RE.sub(var_name, expr)


def _infer_cpp_list_type(items: Sequence[str]) -> str:
    if not items:
        return ""
    if all(item.startswith('"') and item.endswith('"') for item in items):
        return "std::vector<std::string>"
    if all(re.fullmatch(r"-?\d+", item) for item in items):
        return "std::vector<int>"
    return "std::vector"


def _translate_cpp_literal(expr: str, features: Set[str]) -> str:
    stripped = expr.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return stripped
    features.add("vector")
    inner = stripped[1:-1].strip()
    if not inner:
        return "std::vector<int>{}"
    items = split_top_level_args(inner)
    if any(item.startswith('"') and item.endswith('"') for item in items):
        features.add("string")
    rendered = ", ".join(_translate_cpp_literal(item, features) for item in items)
    vector_type = _infer_cpp_list_type(items)
    if vector_type == "std::vector":
        return f"std::vector{{{rendered}}}"
    return f"{vector_type}{{{rendered}}}"


def _expand_macro(name: str, args: List[str], features: Set[str]) -> str:
    if name == "SFM":
        seq, cond, expr = args
        features.update({"numeric", "algorithm", "vector"})
        return (
            f"tl_sum(tl_filter_map({seq}, [&](const auto& it) {{ "
            f"return {_replace_placeholder(cond, 'it')}; }}, "
            f"[&](const auto& it) {{ return {_replace_placeholder(expr, 'it')}; }}))"
        )
    if name == "CF":
        seq, cond = args
        features.add("algorithm")
        return (
            f"tl_count_if({seq}, [&](const auto& it) {{ "
            f"return {_replace_placeholder(cond, 'it')}; }})"
        )
    if name == "S":
        features.add("numeric")
        return f"tl_sum({args[0]})"
    if name == "F":
        seq, cond = args
        features.update({"algorithm", "vector"})
        return f"tl_filter({seq}, [&](const auto& it) {{ return {_replace_placeholder(cond, 'it')}; }})"
    if name == "M":
        seq, expr = args
        features.add("vector")
        return f"tl_map({seq}, [&](const auto& it) {{ return {_replace_placeholder(expr, 'it')}; }})"
    if name == "FM":
        seq, cond, expr = args
        features.update({"algorithm", "vector"})
        return (
            f"tl_filter_map({seq}, [&](const auto& it) {{ "
            f"return {_replace_placeholder(cond, 'it')}; }}, "
            f"[&](const auto& it) {{ return {_replace_placeholder(expr, 'it')}; }})"
        )
    if name == "A":
        seq, cond = args
        features.add("algorithm")
        return f"tl_any({seq}, [&](const auto& it) {{ return {_replace_placeholder(cond, 'it')}; }})"
    if name == "E":
        seq, cond = args
        features.add("algorithm")
        return f"tl_all({seq}, [&](const auto& it) {{ return {_replace_placeholder(cond, 'it')}; }})"
    raise DSLCompileError(f"Unsupported macro `{name}` for C++ translator")


def rewrite_cpp_expression(expr: str, features: Set[str]) -> str:
    out: List[str] = []
    index = 0
    while index < len(expr):
        matched = False
        for name in sorted(_MACRO_NAMES, key=len, reverse=True):
            token = f"{name}("
            if expr.startswith(token, index):
                end = find_matching_paren(expr, index + len(name))
                raw_args = expr[index + len(token):end]
                args = [rewrite_cpp_expression(arg, features) for arg in split_top_level_args(raw_args)]
                expected = {"SFM": 3, "CF": 2, "S": 1, "F": 2, "M": 2, "FM": 3, "A": 2, "E": 2}[name]
                if len(args) != expected:
                    raise DSLCompileError(f"{name} expects exactly {expected} arguments")
                out.append(_expand_macro(name, args, features))
                index = end + 1
                matched = True
                break
        if matched:
            continue
        out.append(expr[index])
        index += 1
    rewritten = "".join(out)
    if "len(" in rewritten:
        features.add("len")
        rewritten = re.sub(r"\blen\(", "tl_len(", rewritten)
    if '"' in rewritten:
        features.add("string")
    return _translate_cpp_literal(rewritten, features)


def _convert_cpp_params(rest: str) -> str:
    name, _, arg_blob = rest.partition("(")
    args = arg_blob[:-1].strip()
    if not args:
        return f"template <class = void>\nauto {name.strip()}()"
    params = ", ".join(f"const auto& {arg.strip()}" for arg in args.split(",") if arg.strip())
    return f"auto {name.strip()}({params})"


def _translate_statement(text: str, line_number: int, features: Set[str]) -> str:
    if text == ":":
        return "else"
    parts = text.split(" ", 1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    if head == "f":
        return _convert_cpp_params(tail)
    if head == "?":
        return f"if ({rewrite_cpp_expression(tail, features)})"
    if head == "w":
        return f"while ({rewrite_cpp_expression(tail, features)})"
    if head == "for":
        return f"for ({tail})"
    if head == "=":
        name, sep, expr = tail.partition(" ")
        if not sep or not name or not expr:
            raise DSLCompileError(
                f"Line {line_number}: assignment must look like `= name expression`"
            )
        return f"auto {name} = {rewrite_cpp_expression(expr, features)};"
    if head == "r":
        return f"return {rewrite_cpp_expression(tail, features)};"
    if head == "p":
        features.add("iostream")
        return f"tl_print({rewrite_cpp_expression(tail, features)});"
    if head == "py":
        return tail
    return rewrite_cpp_expression(text, features) + ";"


def _requires_block(text: str) -> bool:
    return text == ":" or text.startswith(("f ", "? ", "w ", "for "))


def _emit_cpp_lines(lines: Sequence[Line], start: int, indent: int, features: Set[str]) -> Tuple[List[str], int]:
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
        statement = _translate_statement(line.text, line.number, features)
        if _requires_block(line.text):
            if not has_child:
                raise DSLCompileError(
                    f"Line {line.number}: block header must be followed by an indented body"
                )
            if "\n" in statement:
                header, block_header = statement.split("\n", 1)
                out.append(("    " * indent) + header)
                out.append(("    " * indent) + block_header + " {")
            else:
                out.append(("    " * indent) + statement + " {")
            child_lines, new_index = _emit_cpp_lines(lines, index + 1, indent + 1, features)
            out.extend(child_lines)
            out.append(("    " * indent) + "}")
            index = new_index
            continue
        out.append(("    " * indent) + statement)
        index += 1
    return out, index


def _render_helpers(features: Set[str]) -> List[str]:
    out: List[str] = []
    if "len" in features:
        out += [
            "template <class T>",
            "auto tl_len(const T& value) {",
            "    return static_cast<int>(value.size());",
            "}",
            "",
        ]
    if "numeric" in features:
        out += [
            "template <class Seq>",
            "auto tl_sum(const Seq& seq) {",
            "    using Value = typename Seq::value_type;",
            "    return std::accumulate(seq.begin(), seq.end(), Value{});",
            "}",
            "",
        ]
    if "algorithm" in features:
        out += [
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
            "template <class Seq, class Pred>",
            "int tl_count_if(const Seq& seq, Pred pred) {",
            "    return static_cast<int>(std::count_if(seq.begin(), seq.end(), pred));",
            "}",
            "",
        ]
    if "iostream" in features:
        out += [
            "template <class T>",
            "void tl_print(const T& value) {",
            "    std::cout << value << std::endl;",
            "}",
            "",
        ]
        if "vector" in features:
            out += [
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
    return out


def translate_source_cpp(source: str) -> str:
    lines = normalize_lines(source)
    function_blocks, main_lines = split_top_level_blocks(lines)
    features: Set[str] = set()
    body_sections: List[str] = []
    for block in function_blocks:
        body, _ = _emit_cpp_lines(block, 0, 0, features)
        body_sections.extend(body)
        body_sections.append("")
    main_section = ["int main() {"]
    if main_lines:
        body, _ = _emit_cpp_lines(main_lines, 0, 0, features)
        for line in body:
            main_section.append("    " + line)
    main_section += ["    return 0;", "}", ""]

    includes: List[str] = []
    if "algorithm" in features:
        includes.append("#include <algorithm>")
    if "iostream" in features:
        includes.append("#include <iostream>")
    if "numeric" in features:
        includes.append("#include <numeric>")
    if "string" in features:
        includes.append("#include <string>")
    if "vector" in features or "algorithm" in features:
        includes.append("#include <vector>")

    rendered: List[str] = includes + [""]
    rendered.extend(_render_helpers(features))
    rendered.extend(body_sections)
    rendered.extend(main_section)
    return "\n".join(rendered)
