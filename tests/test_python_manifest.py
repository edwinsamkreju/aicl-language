from __future__ import annotations

import json
import sys
from types import ModuleType

import pytest

from aicl.cli import main
from aicl.errors import AICLError
from aicl.python_interop import build_manifest


def add(left: int, right: int) -> int:
    return left + right


def label(value: str, *, prefix: str = "x") -> str:
    return prefix + value


def untyped(value):
    return value


def variadic(*values: int) -> int:
    return len(values)


@pytest.fixture()
def module():
    result = ModuleType("aicl_manifest_fixture")
    result.add = add
    result.label = label
    result.untyped = untyped
    result.variadic = variadic
    return result


def test_manifest_contains_only_requested_signatures_and_is_deterministic(module):
    first = build_manifest(module, ["label", "add"])
    second = build_manifest(module, ["add", "label"])
    assert first == second
    assert [entry["name"] for entry in first["exports"]] == ["add", "label"]
    assert first["exports"][0]["parameters"][0] == {
        "name": "left", "type": "i64", "kind": "positional_or_keyword", "required": True,
    }
    assert first["exports"][1]["parameters"][1]["kind"] == "keyword_only"
    assert first["exports"][1]["parameters"][1]["required"] is False
    assert first["exports"][0]["capability"] == "python:aicl_manifest_fixture.add"
    assert first["binding_hash"].startswith("sha256:")


@pytest.mark.parametrize("symbols", [[], ["missing"], ["_private"], ["untyped"], ["variadic"]])
def test_manifest_rejects_unavailable_or_unsafe_signatures(module, symbols):
    with pytest.raises(AICLError):
        build_manifest(module, symbols)


def test_manifest_rejects_duplicate_exports(module):
    with pytest.raises(AICLError, match="Duplicate export"):
        build_manifest(module, ["add", "add"])


def test_manifest_supports_nested_list_annotations():
    local = ModuleType("aicl_nested_fixture")
    def flatten(values: list[list[int]]) -> list[int]:
        return [item for group in values for item in group]
    local.flatten = flatten
    manifest = build_manifest(local, ["flatten"])
    assert manifest["exports"][0]["parameters"][0]["type"] == "List[List[i64]]"
    assert manifest["exports"][0]["return_type"] == "List[i64]"

    local.flatten.__annotations__ = {
        "values": "typing.List[typing.List[int]]",
        "return": "typing.List[int]",
    }
    qualified = build_manifest(local, ["flatten"])
    assert qualified["exports"][0]["parameters"][0]["type"] == "List[List[i64]]"


def test_manifest_cli_emits_compact_json(monkeypatch, capsys, module):
    monkeypatch.setitem(sys.modules, module.__name__, module)
    assert main(["py-manifest", module.__name__, "add"]) == 0
    output = capsys.readouterr().out
    assert "\n" not in output.strip()
    assert json.loads(output)["exports"][0]["name"] == "add"
