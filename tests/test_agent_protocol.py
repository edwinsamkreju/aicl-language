from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from aicl.agent import PROTOCOL, dispatch_request, run_agent
from aicl.errors import AICLError
from aicl.ir import module_hash
from aicl.syntax import parse_module


SOURCE = """aicl 0.1
f scale(x:i64)->i64 !pure = x * 2
f twice(x:i64)->i64 !pure = x + x
c offset:i64 = 4
"""


def request(**values):
    return {"protocol": PROTOCOL, **values}


def test_module_inspection_returns_signatures_without_expression_bodies():
    response, updated = dispatch_request(SOURCE, request(op="inspect", target="module"))
    assert updated is None
    assert response["ok"] is True
    assert response["module"]["functions"][0]["name"] == "scale"
    assert "body" not in response["module"]["functions"][0]


def test_function_inspection_returns_only_selected_function_tree():
    response, _ = dispatch_request(SOURCE, request(op="inspect", target="function", name="scale"))
    assert response["function"]["name"] == "scale"
    assert response["function"]["body"]["id"] == "n:scale:body"
    assert "twice" not in json.dumps(response)


def test_node_inspection_returns_only_requested_subtree():
    response, _ = dispatch_request(SOURCE, request(op="inspect", target="node", id="n:scale:body/right"))
    assert response["node"]["id"] == "n:scale:body/right"
    assert response["node"]["value"] == 2
    assert response["node"]["op"] == "literal"


def test_check_returns_hash_and_structured_success():
    response, _ = dispatch_request(SOURCE, request(op="check"))
    assert response["ok"] is True
    assert response["functions_checked"] == 2
    assert response["constants_checked"] == 1
    assert response["diagnostics"] == []


def test_patch_request_is_hash_guarded_and_returns_replacement_source():
    base_hash = module_hash(parse_module(SOURCE))
    patch = f"aicl-patch 0.2\nbase {base_hash}\nnode scale n:scale:body/right = 3\n"
    response, updated = dispatch_request(SOURCE, request(op="patch", patch=patch))
    assert response["ok"] is True
    assert updated is not None
    assert "x * 3" in updated


def test_stale_patch_is_rejected_without_replacement():
    patch = "aicl-patch 0.2\nbase sha256:" + "0" * 64 + "\nnode scale n:scale:body/right = 3\n"
    with pytest.raises(AICLError, match="Stale base hash"):
        dispatch_request(SOURCE, request(op="patch", patch=patch))


def test_unknown_node_and_unknown_fields_are_rejected():
    with pytest.raises(AICLError, match="does not exist"):
        dispatch_request(SOURCE, request(op="inspect", target="node", id="n:scale:missing"))
    with pytest.raises(AICLError, match="Invalid fields"):
        dispatch_request(SOURCE, request(op="inspect", target="module", extra=True))


def test_jsonl_agent_processes_inspect_then_patch_then_check(tmp_path: Path):
    source_path = tmp_path / "module.aicl"
    source_path.write_text(SOURCE, encoding="utf-8")
    base_hash = module_hash(parse_module(SOURCE))
    patch = f"aicl-patch 0.2\nbase {base_hash}\nnode scale n:scale:body/right = 5\n"
    lines = [
        json.dumps(request(op="inspect", target="module")),
        json.dumps(request(op="patch", patch=patch)),
        json.dumps(request(op="check")),
    ]
    output = io.StringIO()
    exit_code = run_agent(source_path, io.StringIO("\n".join(lines) + "\n"), output)
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert exit_code == 0
    assert [item["ok"] for item in responses] == [True, True, True]
    assert "x * 5" in source_path.read_text(encoding="utf-8")


def test_invalid_json_is_reported_as_machine_readable_error(tmp_path: Path):
    source_path = tmp_path / "module.aicl"
    source_path.write_text(SOURCE, encoding="utf-8")
    output = io.StringIO()
    exit_code = run_agent(source_path, io.StringIO("{bad json}\n"), output)
    response = json.loads(output.getvalue())
    assert exit_code == 2
    assert response["ok"] is False
    assert response["error"]["code"] == "E-AGENT-013"
