from __future__ import annotations

import json
from pathlib import Path

from aicl.cli import main
from aicl.ir import ir_document
from aicl.syntax import parse_module


def test_compact_ir_is_semantically_identical_to_pretty_ir(capsys):
    assert main(["ir", "examples/clamp.aicl"]) == 0
    pretty = json.loads(capsys.readouterr().out)
    assert main(["ir", "examples/clamp.aicl", "--compact"]) == 0
    compact_text = capsys.readouterr().out
    compact = json.loads(compact_text)
    assert compact == pretty
    assert len(compact_text) < len(json.dumps(pretty, indent=2, ensure_ascii=False, sort_keys=True) + "\\n")


def test_hash_only_matches_canonical_ir_document(capsys):
    program = parse_module(Path("examples/clamp.aicl").read_text(encoding="utf-8"))
    expected = ir_document(program)["module_hash"]
    assert main(["ir", "examples/clamp.aicl", "--hash-only"]) == 0
    assert capsys.readouterr().out.strip() == expected


def test_ir_contract_schema_is_versioned_and_strict():
    schema = json.loads(Path("spec/aicl-ir-0.1.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["ir"]["properties"]["schema"]["const"] == "aicl-ir/0.1"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["module_hash"]["pattern"] == "^sha256:[0-9a-f]{64}$"
