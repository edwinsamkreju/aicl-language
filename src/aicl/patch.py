"""Transactional, hash-guarded whole-body and node-level source patches."""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .errors import AICLError
from .ir import module_hash
from .semantics import check_program
from .syntax import Expr, parse_expression, parse_module


def _child_names(expression: Expr) -> tuple[str, ...]:
    if expression.kind in {"binary", "pipe"}:
        return ("left", "right")
    if expression.kind == "unary":
        return ("operand",)
    return tuple(f"arg{index}" for index in range(len(expression.children)))


def _replace_node(expression: Expr, function_name: str, path: str, target_id: str, replacement: Expr) -> tuple[Expr, bool]:
    """Replace exactly one IR-addressed expression, preserving sibling nodes."""
    if f"n:{function_name}:{path}" == target_id:
        return replacement, True
    children = list(expression.children)
    found = False
    for index, (child, child_name) in enumerate(zip(expression.children, _child_names(expression))):
        updated, matched = _replace_node(child, function_name, f"{path}/{child_name}", target_id, replacement)
        if matched:
            if found:
                raise AICLError("E-PATCH-008", f"Node ID {target_id!r} is ambiguous")
            children[index] = updated
            found = True
    if not found:
        return expression, False
    return replace(expression, children=tuple(children)), True


def _render(expression: Expr) -> str:
    """Render a valid, unambiguous expression; parentheses preserve the AST."""
    if expression.kind == "literal":
        return json.dumps(expression.value, ensure_ascii=False, separators=(",", ":"))
    if expression.kind == "name":
        return str(expression.value)
    if expression.kind == "unary":
        return f"({expression.value}{_render(expression.children[0])})"
    if expression.kind == "binary":
        left, right = expression.children
        return f"({_render(left)} {expression.value} {_render(right)})"
    if expression.kind == "call":
        return f"{expression.value}({', '.join(_render(child) for child in expression.children)})"
    if expression.kind == "pipe":
        left, right = expression.children
        return f"({_render(left)} |> {_render(right)})"
    raise AICLError("E-PATCH-009", f"Cannot render expression node {expression.kind!r}")


def _replace_function_expression(lines: list[str], function, expression: Expr) -> None:
    original = lines[function.line_index]
    prefix, separator, _old_expression = original.partition("=")
    if not separator:
        raise AICLError("E-PATCH-005", f"Could not locate body of function {function.name}")
    lines[function.line_index] = prefix.rstrip() + " = " + _render(expression)


def apply_patch_text(source: str, patch_data: dict[str, Any]) -> str:
    program = parse_module(source)
    expected_hash = patch_data.get("base_hash")
    actual_hash = module_hash(program)
    if expected_hash != actual_hash:
        raise AICLError("E-PATCH-001", f"Stale base hash: expected {expected_hash!r}, current module is {actual_hash}")
    operations = patch_data.get("operations")
    if not isinstance(operations, list) or not operations:
        raise AICLError("E-PATCH-002", "Patch must contain a non-empty operations array")

    lines = list(program.source_lines)
    patched_nodes: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise AICLError("E-PATCH-003", "Each patch operation must be an object")
        op_kind = operation.get("op")
        name = operation.get("function")
        current_source = "\n".join(lines) + ("\n" if source.endswith("\n") else "")
        current_program = parse_module(current_source)
        functions = {item.name: item for item in current_program.functions}
        if name not in functions:
            raise AICLError("E-PATCH-004", "Patch operation must identify an existing function")
        function = functions[name]

        if op_kind == "replace_body":
            expression_source = operation.get("expression")
            if not isinstance(expression_source, str):
                raise AICLError("E-PATCH-004", "replace_body requires an expression string")
            expression = parse_expression(expression_source)
            _replace_function_expression(lines, function, expression)
        elif op_kind == "replace_node":
            node_id = operation.get("node_id")
            expression_source = operation.get("expression")
            if not isinstance(node_id, str) or not isinstance(expression_source, str):
                raise AICLError("E-PATCH-004", "replace_node requires node_id and expression strings")
            if node_id in patched_nodes:
                raise AICLError("E-PATCH-010", f"Node {node_id!r} is patched more than once")
            replacement = parse_expression(expression_source)
            updated_body, matched = _replace_node(function.body, function.name, "body", node_id, replacement)
            if not matched:
                raise AICLError("E-PATCH-011", f"Node ID {node_id!r} does not exist in function {name!r}")
            _replace_function_expression(lines, function, updated_body)
            patched_nodes.add(node_id)
        else:
            raise AICLError("E-PATCH-003", f"Unsupported patch operation {op_kind!r}")

    candidate = "\n".join(lines) + ("\n" if source.endswith("\n") else "")
    candidate_program = parse_module(candidate)
    check_program(candidate_program)
    return candidate


def parse_compact_patch(source: str) -> dict[str, Any]:
    """Decode compact AICL Patch Text 0.2 into the validated patch structure."""
    lines = [line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines or lines[0] != "aicl-patch 0.2":
        raise AICLError("E-PATCH-012", "Compact patch must start with 'aicl-patch 0.2'")
    if len(lines) < 3 or not lines[1].startswith("base "):
        raise AICLError("E-PATCH-013", "Compact patch requires a base hash and at least one operation")
    operations = []
    for line in lines[2:]:
        if line.startswith("node "):
            header, separator, expression = line.partition("=")
            fields = header.split()
            if not separator or len(fields) != 3:
                raise AICLError("E-PATCH-014", f"Invalid compact node patch: {line!r}")
            _, function, node_id = fields
            operations.append({"op": "replace_node", "function": function, "node_id": node_id, "expression": expression.strip()})
        elif line.startswith("body "):
            header, separator, expression = line.partition("=")
            fields = header.split()
            if not separator or len(fields) != 2:
                raise AICLError("E-PATCH-015", f"Invalid compact body patch: {line!r}")
            _, function = fields
            operations.append({"op": "replace_body", "function": function, "expression": expression.strip()})
        else:
            raise AICLError("E-PATCH-016", f"Unknown compact patch instruction: {line!r}")
    return {"base_hash": lines[1][5:].strip(), "operations": operations}


def apply_patch_file(source_path: str | Path, patch_path: str | Path) -> str:
    source_file = Path(source_path)
    patch_file = Path(patch_path)
    try:
        patch_text = patch_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AICLError("E-PATCH-006", f"Cannot read patch file: {exc}") from exc
    try:
        patch_data = parse_compact_patch(patch_text) if patch_text.lstrip().startswith("aicl-patch") else json.loads(patch_text)
    except json.JSONDecodeError as exc:
        raise AICLError("E-PATCH-006", f"Cannot parse patch JSON: {exc}") from exc
    if not isinstance(patch_data, dict):
        raise AICLError("E-PATCH-007", "Patch document must be a JSON object")
    try:
        original = source_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AICLError("E-PATCH-006", f"Cannot read source file: {exc}") from exc
    updated = apply_patch_text(original, patch_data)

    # Atomic replace: no partial source is written if parsing/type checking fails.
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{source_file.name}.", dir=source_file.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, source_file)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return module_hash(parse_module(updated))
