from __future__ import annotations

from pathlib import Path
import sys

import tiktoken

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def count(text: str, encoding_name: str) -> int:
    return len(tiktoken.get_encoding(encoding_name).encode(text))


def main() -> None:
    py_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "benchmarks" / "aggressive_torch_cnn.py"
    aidl_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "benchmarks" / "aggressive_torch_cnn.aidl"
    aidl_ungrouped_path = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "benchmarks" / "aggressive_torch_cnn_ungrouped.aidl"
    if not py_path.is_absolute():
        py_path = (ROOT / py_path).resolve()
    if not aidl_path.is_absolute():
        aidl_path = (ROOT / aidl_path).resolve()
    if not aidl_ungrouped_path.is_absolute():
        aidl_ungrouped_path = (ROOT / aidl_ungrouped_path).resolve()

    python_code = py_path.read_text(encoding="utf-8").strip()
    aidl_code = aidl_path.read_text(encoding="utf-8").strip()
    aidl_ungrouped_code = aidl_ungrouped_path.read_text(encoding="utf-8").strip()
    py_header_code = f"py\n{python_code}"

    print(f"python: {py_path}")
    print(f"aidl: {aidl_path}")
    print(f"aidl_ungrouped: {aidl_ungrouped_path}")
    for encoding_name in ("o200k_base", "cl100k_base"):
        py_tokens = count(python_code, encoding_name)
        aidl_tokens = count(aidl_code, encoding_name)
        aidl_ungrouped_tokens = count(aidl_ungrouped_code, encoding_name)
        py_header_tokens = count(py_header_code, encoding_name)
        print(f"== {encoding_name} ==")
        print(f"python_tokens: {py_tokens}")
        print(f"aidl_tokens: {aidl_tokens}")
        print(f"aidl_ungrouped_tokens: {aidl_ungrouped_tokens}")
        print(f"py_header_tokens: {py_header_tokens}")
        print(f"aidl_saved_vs_python: {py_tokens - aidl_tokens}")
        print(f"aidl_group_saved_vs_ungrouped: {aidl_ungrouped_tokens - aidl_tokens}")
        print(f"py_header_saved_vs_python: {py_tokens - py_header_tokens}")
        print("")


if __name__ == "__main__":
    main()
