from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Sequence, Tuple, Union


@dataclass
class Line:
    number: int
    indent: int
    text: str


class DSLCompileError(ValueError):
    pass


def normalize_lines(source: str) -> List[Line]:
    raw_lines = source.splitlines()
    significant = [
        (number, raw)
        for number, raw in enumerate(raw_lines, start=1)
        if raw.strip() and not raw.strip().startswith("#")
    ]
    if _looks_like_flat_mode(significant):
        return _normalize_flat_lines(significant)
    return _normalize_indented_lines(significant)


def _normalize_indented_lines(significant: Sequence[Tuple[int, str]]) -> List[Line]:
    lines: List[Line] = []
    for number, raw in significant:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2 != 0:
            raise DSLCompileError(
                f"Line {number}: indentation must use multiples of 2 spaces"
            )
        lines.append(Line(number=number, indent=indent // 2, text=stripped))
    return lines


_FLAT_SUFFIX_RE = re.compile(r"^(?P<text>.*?)(?: (?P<next>[0-9]))?$")


def _looks_like_flat_mode(significant: Sequence[Tuple[int, str]]) -> bool:
    if not significant:
        return False
    if any(raw.startswith(" ") for _, raw in significant):
        return False
    return all(_FLAT_SUFFIX_RE.match(raw.rstrip()) is not None for _, raw in significant)


def _normalize_flat_lines(significant: Sequence[Tuple[int, str]]) -> List[Line]:
    lines: List[Line] = []
    current_indent_spaces = 0
    for index, (number, raw) in enumerate(significant):
        if raw.startswith(" "):
            raise DSLCompileError(
                f"Line {number}: flat AIDL form must keep every line left-aligned"
            )
        match = _FLAT_SUFFIX_RE.match(raw.rstrip())
        if match is None:
            raise DSLCompileError(f"Line {number}: invalid flat AIDL line")
        text = match.group("text")
        next_indent_text = match.group("next")
        next_indent_spaces = int(next_indent_text) if next_indent_text is not None else 0
        if current_indent_spaces % 2 != 0:
            raise DSLCompileError(
                f"Line {number}: current indentation in flat mode must be an even number of spaces"
            )
        if next_indent_spaces % 2 != 0:
            raise DSLCompileError(
                f"Line {number}: next-line indentation in flat mode must be an even number of spaces"
            )
        if next_indent_spaces > 8:
            raise DSLCompileError(
                f"Line {number}: flat mode currently supports at most 8 spaces of indentation"
            )
        if not text.strip():
            raise DSLCompileError(f"Line {number}: flat AIDL line cannot be empty")
        lines.append(
            Line(number=number, indent=current_indent_spaces // 2, text=text.strip())
        )
        if index == len(significant) - 1 and next_indent_text is None:
            current_indent_spaces = 0
        else:
            current_indent_spaces = next_indent_spaces
    return lines


def render_flat_aidl(source: str) -> str:
    lines = normalize_lines(source)
    out: List[str] = []
    for index, line in enumerate(lines):
        next_indent_spaces = (
            lines[index + 1].indent * 2 if index + 1 < len(lines) else 0
        )
        if next_indent_spaces > 0:
            out.append(f"{line.text} {next_indent_spaces}")
        else:
            out.append(line.text)
    return "\n".join(out) + ("\n" if out else "")


def split_top_level_args(text: str) -> List[str]:
    if not text.strip():
        return []
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


def split_top_level_statements(text: str) -> List[str]:
    if not text.strip():
        return []
    parts: List[str] = []
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
        if char == ";" and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def find_matching_paren(text: str, start: int) -> int:
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


def split_top_level_blocks(lines: Sequence[Line]) -> Tuple[List[List[Line]], List[Line]]:
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


def count_stats(source: str, translated: str) -> Dict[str, int]:
    dsl_chars = len(source)
    target_chars = len(translated)
    dsl_nonempty_lines = len([line for line in source.splitlines() if line.strip()])
    target_nonempty_lines = len(
        [line for line in translated.splitlines() if line.strip()]
    )
    return {
        "dsl_chars": dsl_chars,
        "target_chars": target_chars,
        "char_delta": target_chars - dsl_chars,
        "dsl_nonempty_lines": dsl_nonempty_lines,
        "target_nonempty_lines": target_nonempty_lines,
    }


def read_source(path: Union[str, Path]) -> str:
    return Path(path).read_text(encoding="utf-8")


def iter_examples(example_dir: Union[str, Path]) -> Iterable[Path]:
    yield from sorted(Path(example_dir).glob("*.aidl"))
