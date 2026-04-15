from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import (
    count_stats,
    iter_examples,
    reverse_translate_file,
    run_compiled,
    translate_file,
    translate_source,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI-DSL translators and interpreter")
    sub = parser.add_subparsers(dest="command", required=True)

    translate_cmd = sub.add_parser("translate", help="Translate DSL source into a backend")
    translate_cmd.add_argument("path", help="Path to a .aidl file")
    translate_cmd.add_argument(
        "--target",
        choices=["python", "cpp"],
        default="python",
        help="Translation target backend",
    )

    compile_cmd = sub.add_parser("compile", help="Alias of translate")
    compile_cmd.add_argument("path", help="Path to a .aidl file")
    compile_cmd.add_argument(
        "--target",
        choices=["python", "cpp"],
        default="python",
        help="Translation target backend",
    )

    run_cmd = sub.add_parser("run", help="Interpret a .aidl file via the Python translator")
    run_cmd.add_argument("path", help="Path to a .aidl file")

    reverse_cmd = sub.add_parser("reverse", help="Translate a Python file into AIDL")
    reverse_cmd.add_argument("path", help="Path to a .py file")

    stats_cmd = sub.add_parser("stats", help="Show simple size statistics after Python translation")
    stats_cmd.add_argument("path", help="Path to a .aidl file")

    examples_cmd = sub.add_parser("examples", help="List bundled examples")
    examples_cmd.add_argument(
        "--dir",
        default=str(Path(__file__).resolve().parents[2] / "examples"),
        help="Directory containing .aidl examples",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in {"translate", "compile"}:
        print(translate_file(args.path, target=args.target), end="")
        return

    if args.command == "run":
        source = Path(args.path).read_text(encoding="utf-8")
        run_compiled(source, filename=args.path)
        return

    if args.command == "reverse":
        print(reverse_translate_file(args.path), end="")
        return

    if args.command == "stats":
        source = Path(args.path).read_text(encoding="utf-8")
        compiled = translate_source(source, target="python")
        stats = count_stats(source, compiled)
        for key, value in stats.items():
            print(f"{key}: {value}")
        return

    if args.command == "examples":
        for path in iter_examples(args.dir):
            print(path)
        return

    raise AssertionError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
