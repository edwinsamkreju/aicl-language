from __future__ import annotations
from pathlib import Path
import pytest
from aicl.errors import AICLError
from aicl.ir import canonical_json,module_hash
from aicl.patch import apply_patch_text
from aicl.semantics import run_function
from aicl.syntax import parse_module
ROOT=Path(__file__).resolve().parents[1]
def source(name): return (ROOT/"examples"/name).read_text(encoding="utf-8")
def test_clamp_executes_and_checks_types():
 p=parse_module(source("clamp.aicl"))
 assert run_function(p,"clamp",[15,0,10])==10
 assert run_function(p,"clamp",[-4,0,10])==0
 assert run_function(p,"clamp",[4,0,10])==4
def test_pipeline_map_filter_unique():
 p=parse_module(source("text_pipeline.aicl"))
 assert run_function(p,"clean",[[" A ","","B","A"," B "]])==["A","B"]
def test_canonical_ir_and_hash_are_deterministic():
 a=parse_module(source("clamp.aicl")); b=parse_module("\n"+source("clamp.aicl"))
 assert canonical_json(a)==canonical_json(b); assert module_hash(a)==module_hash(b)
 rendered=canonical_json(a); assert '"id": "n:clamp:body"' in rendered; assert '"type": "i64"' in rendered
def test_pipeline_ir_keeps_callback_type():
 assert '"type": "Fn[Str,Str]"' in canonical_json(parse_module(source("text_pipeline.aicl")))
def test_bad_type_is_rejected():
 from aicl.semantics import check_program
 with pytest.raises(AICLError,match="Cannot apply"): check_program(parse_module("aicl 0.1\nf wrong(x:Str)->i64 !pure = x + 1\n"))
def test_patch_is_hash_guarded_and_transactional():
 original=source("patchable.aicl"); p=parse_module(original)
 patch={"base_hash":module_hash(p),"operations":[{"op":"replace_body","function":"scale","expression":"x * 3"}]}
 updated=apply_patch_text(original,patch); assert "x * 3" in updated
 assert run_function(parse_module(updated),"scale",[7])==21
 with pytest.raises(AICLError,match="Stale base hash"): apply_patch_text(original,{**patch,"base_hash":"sha256:stale"})
def test_unary_boolean_operator_and_constants():
 p=parse_module("aicl 0.1\nc offset:i64 = 4\nf invert(x:bool)->bool !pure = !x\nf add_offset(x:i64)->i64 !pure = x + offset\n")
 assert run_function(p,"invert",[True]) is False; assert run_function(p,"add_offset",[8])==12
def test_i64_literal_range_is_checked():
 from aicl.semantics import check_program
 with pytest.raises(AICLError,match="outside the signed i64 range"): check_program(parse_module("aicl 0.1\nf too_large()->i64 !pure = 9223372036854775808\n"))
def test_patch_rejects_type_invalid_candidate():
 original=source("patchable.aicl")
 patch={"base_hash":module_hash(parse_module(original)),"operations":[{"op":"replace_body","function":"scale","expression":'"not an integer"'}]}
 with pytest.raises(AICLError,match="expected i64"): apply_patch_text(original,patch)
