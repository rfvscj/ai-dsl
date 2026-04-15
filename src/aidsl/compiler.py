from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

from .cpp_translator import translate_source_cpp
from .frontend import DSLCompileError, count_stats, iter_examples, read_source
from .python_translator import run_translated_python, translate_source_python


def translate_source(source: str, target: str = "python") -> str:
    if target == "python":
        return translate_source_python(source)
    if target == "cpp":
        return translate_source_cpp(source)
    raise DSLCompileError(f"Unsupported target `{target}`")


def translate_file(path: Union[str, Path], target: str = "python") -> str:
    return translate_source(read_source(path), target=target)


def compile_source(source: str) -> str:
    return translate_source_python(source)


def compile_source_cpp(source: str) -> str:
    return translate_source_cpp(source)


def compile_file(path: Union[str, Path], target: str = "python") -> str:
    return translate_file(path, target=target)


def run_compiled(source: str, filename: str = "<aidsl>") -> Dict[str, object]:
    return run_translated_python(source, filename=filename)
