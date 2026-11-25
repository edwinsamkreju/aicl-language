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
    assert first["schema"] == "aicl-python-bindings/0.2"
    assert first["python"]["implementation"]
    assert [entry["name"] for entry in first["exports"]] == ["add", "label"]
    assert first["exports"][0]["parameters"][0] == {
        "name": "left", "type": "i64", "kind": "positional_or_keyword", "required": True,
    }
    assert first["exports"][1]["parameters"][1]["kind"] == "keyword_only"
    assert first["exports"][1]["parameters"][1]["required"] is False
    assert first["exports"][0]["capability"] == "python:aicl_manifest_fixture.add"
    assert first["exports"][0]["type_source"] == "annotations"
    assert first["exports"][0]["signature_verified"] is True
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



def test_explicit_declaration_supports_unannotated_native_style_functions(module):
    declaration = {
        "untyped": {
            "parameters": [{
                "name": "value",
                "type": "i64",
                "kind": "positional_or_keyword",
                "required": True,
            }],
            "return_type": "i64",
        }
    }
    manifest = build_manifest(module, ["untyped"], declarations=declaration)
    entry = manifest["exports"][0]
    assert entry["type_source"] == "explicit"
    assert entry["signature_verified"] is True
    assert entry["parameters"][0]["type"] == "i64"


def test_explicit_declaration_reports_signature_mismatch(module):
    declaration = {
        "untyped": {
            "parameters": [{
                "name": "value",
                "type": "i64",
                "kind": "keyword_only",
                "required": True,
            }],
            "return_type": "i64",
        }
    }
    manifest = build_manifest(module, ["untyped"], declarations=declaration)
    assert manifest["exports"][0]["signature_verified"] is False


def test_explicit_declaration_rejects_unknown_types(module):
    declaration = {
        "untyped": {
            "parameters": [{
                "name": "value",
                "type": "Tensor[f32]",
                "kind": "positional_or_keyword",
                "required": True,
            }],
            "return_type": "i64",
        }
    }
    with pytest.raises(AICLError, match="Unsupported AICL type"):
        build_manifest(module, ["untyped"], declarations=declaration)


def test_manifest_cli_accepts_explicit_declarations(tmp_path, monkeypatch, capsys, module):
    monkeypatch.setitem(sys.modules, module.__name__, module)
    declaration = {
        "untyped": {
            "parameters": [{
                "name": "value",
                "type": "i64",
                "kind": "positional_or_keyword",
                "required": True,
            }],
            "return_type": "i64",
        }
    }
    path = tmp_path / "bindings.json"
    path.write_text(json.dumps(declaration), encoding="utf-8")
    assert main(["py-manifest", module.__name__, "untyped", "--declarations", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["exports"][0]["type_source"] == "explicit"


def test_binding_schema_02_describes_versioned_types_and_python_environment():
    from pathlib import Path
    schema = json.loads(
        Path("spec/aicl-python-bindings-0.2.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["schema"]["const"] == "aicl-python-bindings/0.2"
    assert "python" in schema["required"]
    export = schema["properties"]["exports"]["items"]
    assert "type_source" in export["required"]
    assert "signature_verified" in export["required"]
