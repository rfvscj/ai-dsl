from __future__ import annotations

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


def normalize_lines(source: str) -> List[Line]:
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


def split_top_level_args(text: str) -> List[str]:
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
