from __future__ import annotations

import ast
import textwrap
from typing import List, Optional

from .frontend import render_flat_aidl


def _indent(level: int) -> str:
    return "  " * level


def _src(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is not None:
        return segment
    if hasattr(ast, "unparse"):
        return ast.unparse(node)
    raise ValueError("Cannot recover source segment for node")


def _line_to_py(line: str, level: int) -> str:
    if line.strip():
        return f"{_indent(level)}py {line.rstrip()}"
    return ""


def _emit_raw_block(source: str, node: ast.AST, level: int) -> List[str]:
    segment = _src(source, node)
    dedented = textwrap.dedent(segment)
    lines: List[str] = []
    for line in dedented.splitlines():
        rendered = _line_to_py(line, level)
        if rendered:
            lines.append(rendered)
    return lines


def _simple_assign_target(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_single_line(text: str) -> bool:
    return "\n" not in text and "\r" not in text


class _PythonToAIDL:
    def __init__(self, source: str):
        self.source = source

    def convert(self) -> str:
        tree = ast.parse(self.source)
        lines: List[str] = []
        for stmt in tree.body:
            lines.extend(self.emit_stmt(stmt, 0))
        return "\n".join(lines) + ("\n" if lines else "")

    def emit_body(self, body: List[ast.stmt], level: int) -> List[str]:
        lines: List[str] = []
        for stmt in body:
            lines.extend(self.emit_stmt(stmt, level))
        return lines

    def emit_stmt(self, node: ast.stmt, level: int) -> List[str]:
        if isinstance(node, ast.FunctionDef):
            header = f"{_indent(level)}f {node.name}({self._args(node.args)})"
            lines = [header]
            for deco in node.decorator_list:
                lines.insert(0, f"{_indent(level)}py @{_src(self.source, deco)}")
            return lines + self.emit_body(node.body, level + 1)
        if isinstance(node, ast.Return):
            if node.value is None:
                return [f"{_indent(level)}py return"]
            value = _src(self.source, node.value)
            if _is_single_line(value):
                return [f"{_indent(level)}r {value}"]
            return _emit_raw_block(self.source, node, level)
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = _simple_assign_target(node.targets[0])
            value = _src(self.source, node.value)
            if target is not None and _is_single_line(value):
                return [f"{_indent(level)}= {target} {value}"]
            return _emit_raw_block(self.source, node, level)
        if isinstance(node, ast.AnnAssign):
            target = _simple_assign_target(node.target)
            if target is not None and node.value is not None:
                value = _src(self.source, node.value)
                if _is_single_line(value):
                    return [f"{_indent(level)}= {target} {value}"]
            return _emit_raw_block(self.source, node, level)
        if isinstance(node, ast.AugAssign):
            return [f"{_indent(level)}py {_src(self.source, node)}"]
        if isinstance(node, ast.Expr):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "print":
                if len(value.args) == 1 and not value.keywords:
                    arg = _src(self.source, value.args[0])
                    if _is_single_line(arg):
                        return [f"{_indent(level)}p {arg}"]
            return _emit_raw_block(self.source, node, level)
        if isinstance(node, ast.If):
            lines = [f"{_indent(level)}? {_src(self.source, node.test)}"]
            lines.extend(self.emit_body(node.body, level + 1))
            if node.orelse:
                lines.append(f"{_indent(level)}:")
                lines.extend(self.emit_body(node.orelse, level + 1))
            return lines
        if isinstance(node, ast.For):
            target = _src(self.source, node.target)
            iterator = _src(self.source, node.iter)
            lines = [f"{_indent(level)}for {target} in {iterator}"]
            lines.extend(self.emit_body(node.body, level + 1))
            if node.orelse:
                lines.append(f"{_indent(level)}py else:")
                lines.extend(self.emit_body(node.orelse, level + 1))
            return lines
        if isinstance(node, ast.While):
            lines = [f"{_indent(level)}w {_src(self.source, node.test)}"]
            lines.extend(self.emit_body(node.body, level + 1))
            if node.orelse:
                lines.append(f"{_indent(level)}py else:")
                lines.extend(self.emit_body(node.orelse, level + 1))
            return lines
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass, ast.Break, ast.Continue, ast.Raise, ast.Assert, ast.Delete, ast.Global, ast.Nonlocal)):
            return [f"{_indent(level)}py {_src(self.source, node)}"]
        return _emit_raw_block(self.source, node, level)

    def _args(self, args: ast.arguments) -> str:
        parts: List[str] = []
        for arg in args.posonlyargs:
            parts.append(arg.arg)
        if args.posonlyargs:
            parts.append("/")
        for arg in args.args:
            parts.append(arg.arg)
        if args.vararg is not None:
            parts.append(f"*{args.vararg.arg}")
        elif args.kwonlyargs:
            parts.append("*")
        for arg in args.kwonlyargs:
            parts.append(arg.arg)
        if args.kwarg is not None:
            parts.append(f"**{args.kwarg.arg}")
        return ", ".join(parts)


def reverse_translate_python(source: str) -> str:
    indented = _PythonToAIDL(source).convert()
    return render_flat_aidl(indented)
