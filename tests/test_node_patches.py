from pathlib import Path
import pytest
from aicl.errors import AICLError
from aicl.ir import module_hash
from aicl.patch import apply_patch_file,apply_patch_text,parse_compact_patch
from aicl.semantics import run_function
from aicl.syntax import parse_module

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"examples/patchable.aicl").read_text(encoding="utf-8")

def test_patch_one_ir_node_without_rewriting_the_whole_function():
    patch={"base_hash":module_hash(parse_module(SOURCE)),"operations":[{"op":"replace_node","function":"scale","node_id":"n:scale:body/right","expression":"3"}]}
    updated=apply_patch_text(SOURCE,patch)
    assert "(x * 3)" in updated
    assert run_function(parse_module(updated),"scale",[7])==21

def test_compact_patch_profile_decodes_and_executes():
    base=module_hash(parse_module(SOURCE))
    compact=f"aicl-patch 0.2\nbase {base}\nnode scale n:scale:body/right = 3\n"
    updated=apply_patch_text(SOURCE,parse_compact_patch(compact))
    assert run_function(parse_module(updated),"scale",[7])==21

def test_compact_patch_file_is_accepted_by_patch_engine(tmp_path:Path):
    source_path=tmp_path/"module.aicl"; patch_path=tmp_path/"change.aiclp"
    source_path.write_text(SOURCE,encoding="utf-8")
    base=module_hash(parse_module(SOURCE))
    patch_path.write_text(f"aicl-patch 0.2\nbase {base}\nnode scale n:scale:body/right = 3\n",encoding="utf-8")
    apply_patch_file(source_path,patch_path)
    assert run_function(parse_module(source_path.read_text(encoding="utf-8")),"scale",[7])==21

def test_disjoint_node_patches_compose_atomically():
    patch={"base_hash":module_hash(parse_module(SOURCE)),"operations":[
      {"op":"replace_node","function":"scale","node_id":"n:scale:body/right","expression":"3"},
      {"op":"replace_node","function":"scale","node_id":"n:scale:body/left","expression":"x + 1"}]}
    updated=apply_patch_text(SOURCE,patch)
    assert run_function(parse_module(updated),"scale",[7])==24

def test_invalid_node_patch_is_rejected():
    base=module_hash(parse_module(SOURCE))
    unknown={"base_hash":base,"operations":[{"op":"replace_node","function":"scale","node_id":"n:scale:body/missing","expression":"3"}]}
    with pytest.raises(AICLError,match="does not exist"): apply_patch_text(SOURCE,unknown)
    wrong_type={"base_hash":base,"operations":[{"op":"replace_node","function":"scale","node_id":"n:scale:body/right","expression":'"wrong"'}]}
    with pytest.raises(AICLError,match="Cannot apply"): apply_patch_text(SOURCE,wrong_type)

def test_overlapping_node_patches_are_rejected():
    patch={"base_hash":module_hash(parse_module(SOURCE)),"operations":[
      {"op":"replace_node","function":"scale","node_id":"n:scale:body","expression":"x + 1"},
      {"op":"replace_node","function":"scale","node_id":"n:scale:body/left","expression":"x + 2"}]}
    with pytest.raises(AICLError,match="Overlapping patch"): apply_patch_text(SOURCE,patch)
