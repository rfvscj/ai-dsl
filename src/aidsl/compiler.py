from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

from .frontend import DSLCompileError, count_stats, iter_examples, read_source
from .python_translator import run_translated_python, translate_source_python


def translate_source(source: str) -> str:
    return translate_source_python(source)


def translate_file(path: Union[str, Path]) -> str:
    return translate_source(read_source(path))


def compile_source(source: str) -> str:
    return translate_source_python(source)


def compile_file(path: Union[str, Path]) -> str:
    return translate_file(path)


def run_compiled(source: str, filename: str = "<aidsl>") -> Dict[str, object]:
    return run_translated_python(source, filename=filename)
