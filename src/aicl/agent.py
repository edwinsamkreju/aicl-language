"""Compact, line-oriented agent protocol for AICL-C 0.1."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, TextIO

from .errors import AICLError
from .ir import canonical_ir, module_hash
from .patch import apply_patch_text, parse_compact_patch
from .semantics import check_program
from .syntax import parse_module

PROTOCOL = "aicl-agent/0.1"


def _fail(code: str, message: str) -> None:
    raise AICLError(code, message)


def _node_by_id(node: dict[str, Any], wanted: str) -> dict[str, Any] | None:
    if node.get("id") == wanted:
        return node
    for child in node.get("children", []):
        found = _node_by_id(child, wanted)
        if found is not None:
            return found
    return None


def dispatch_request(source: str, request: Any) -> tuple[dict[str, Any], str | None]:
    """Dispatch one request. Return (response, replacement_source)."""
    if not isinstance(request, dict):
        _fail("E-AGENT-001", "Request must be a JSON object")
    if request.get("protocol") != PROTOCOL:
        _fail("E-AGENT-002", f"Expected protocol {PROTOCOL!r}")

    operation = request.get("op")
    if operation == "inspect":
        target = request.get("target")
        allowed = {"protocol", "op", "target"}
        if target == "function":
            allowed.add("name")
        elif target == "node":
            allowed.add("id")
        elif target != "module":
            _fail("E-AGENT-003", "inspect target must be module, function, or node")
        if set(request) != allowed:
            _fail("E-AGENT-004", f"Invalid fields for inspect/{target}")

        program = parse_module(source)
        check_program(program)
        digest = module_hash(program)
        if target == "module":
            return ({
                "protocol": PROTOCOL,
                "ok": True,
                "hash": digest,
                "module": {
                    "version": program.version,
                    "functions": [
                        {
                            "name": fn.name,
                            "parameters": [{"name": p.name, "type": p.type_name} for p in fn.parameters],
                            "return_type": fn.return_type,
                            "effect": fn.effect,
                        }
                        for fn in sorted(program.functions, key=lambda item: item.name)
                    ],
                    "constants": [
                        {"name": item.name, "type": item.type_name}
                        for item in sorted(program.constants, key=lambda item: item.name)
                    ],
                },
            }, None)

        ir = canonical_ir(program)
        if target == "function":
            name = request.get("name")
            if not isinstance(name, str) or not name:
                _fail("E-AGENT-005", "inspect/function requires a non-empty name")
            for function in ir["functions"]:
                if function["name"] == name:
                    return ({"protocol": PROTOCOL, "ok": True, "hash": digest, "function": function}, None)
            _fail("E-AGENT-006", f"Function {name!r} does not exist")

        node_id = request.get("id")
        if not isinstance(node_id, str) or not node_id:
            _fail("E-AGENT-007", "inspect/node requires a non-empty id")
        for function in ir["functions"]:
            found = _node_by_id(function["body"], node_id)
            if found is not None:
                return ({"protocol": PROTOCOL, "ok": True, "hash": digest, "node": found}, None)
        for constant in ir["constants"]:
            found = _node_by_id(constant["initializer"], node_id)
            if found is not None:
                return ({"protocol": PROTOCOL, "ok": True, "hash": digest, "node": found}, None)
        _fail("E-AGENT-008", f"Node {node_id!r} does not exist in this module")

    if operation == "check":
        if set(request) != {"protocol", "op"}:
            _fail("E-AGENT-009", "check accepts only protocol and op")
        program = parse_module(source)
        check_program(program)
        return ({
            "protocol": PROTOCOL,
            "ok": True,
            "hash": module_hash(program),
            "functions_checked": len(program.functions),
            "constants_checked": len(program.constants),
            "diagnostics": [],
        }, None)

    if operation == "patch":
        if set(request) != {"protocol", "op", "patch"}:
            _fail("E-AGENT-010", "patch requires exactly one compact patch string")
        patch_text = request.get("patch")
        if not isinstance(patch_text, str):
            _fail("E-AGENT-011", "patch must be a string containing AICL Patch Text 0.2")
        patch_data = parse_compact_patch(patch_text)
        updated = apply_patch_text(source, patch_data)
        updated_program = parse_module(updated)
        return ({
            "protocol": PROTOCOL,
            "ok": True,
            "hash": module_hash(updated_program),
            "status": "patched",
        }, updated)

    _fail("E-AGENT-012", "op must be inspect, check, or patch")


def _write_atomic(path: Path, source: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _error_response(error: AICLError) -> dict[str, Any]:
    return {"protocol": PROTOCOL, "ok": False, "error": error.as_dict()}


def run_agent(path: str | Path, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> int:
    """Process JSONL requests from stdin and emit one JSONL response per request."""
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    source_path = Path(path)
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        error = AICLError("E-IO-001", f"Cannot read {source_path}: {exc}")
        output_stream.write(json.dumps(_error_response(error), separators=(",", ":"), sort_keys=True) + "\n")
        output_stream.flush()
        return 2

    had_error = False
    for raw_line in input_stream:
        if not raw_line.strip():
            continue
        try:
            try:
                request = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise AICLError("E-AGENT-013", f"Invalid JSON request: {exc.msg}") from exc
            response, updated = dispatch_request(source, request)
            if updated is not None:
                _write_atomic(source_path, updated)
                source = updated
        except AICLError as exc:
            response = _error_response(exc)
            had_error = True
        except OSError as exc:
            response = _error_response(AICLError("E-IO-002", f"Cannot write {source_path}: {exc}"))
            had_error = True
        output_stream.write(json.dumps(response, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
        output_stream.flush()
    return 2 if had_error else 0
