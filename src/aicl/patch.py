"""Transactional source patching based on canonical module hashes."""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any
from .errors import AICLError
from .ir import module_hash
from .semantics import check_program
from .syntax import parse_expression, parse_module

def apply_patch_text(source:str,patch_data:dict[str,Any])->str:
    program=parse_module(source); expected=patch_data.get("base_hash"); actual=module_hash(program)
    if expected!=actual: raise AICLError("E-PATCH-001",f"Stale base hash: expected {expected!r}, current module is {actual}")
    operations=patch_data.get("operations")
    if not isinstance(operations,list) or not operations: raise AICLError("E-PATCH-002","Patch must contain a non-empty operations array")
    lines=list(program.source_lines); functions={f.name:f for f in program.functions}
    for op in operations:
        if not isinstance(op,dict) or op.get("op")!="replace_body": raise AICLError("E-PATCH-003","AICL patch 0.1 supports only replace_body operations")
        name=op.get("function"); expression=op.get("expression")
        if name not in functions or not isinstance(expression,str): raise AICLError("E-PATCH-004","replace_body requires an existing function and expression string")
        parse_expression(expression); f=functions[name]; original=lines[f.line_index]; prefix,sep,_=original.partition("=")
        if not sep: raise AICLError("E-PATCH-005",f"Could not locate body of function {name}")
        lines[f.line_index]=prefix.rstrip()+" = "+expression.strip()
    candidate="\n".join(lines)+("\n" if source.endswith("\n") else "")
    check_program(parse_module(candidate))
    return candidate

def apply_patch_file(source_path:str|Path,patch_path:str|Path)->str:
    source_file=Path(source_path); patch_file=Path(patch_path)
    try:
        source=source_file.read_text(encoding="utf-8"); patch=json.loads(patch_file.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise AICLError("E-PATCH-006",f"Cannot read patch input: {exc}") from exc
    candidate=apply_patch_text(source,patch)
    fd,temp_name=tempfile.mkstemp(prefix=source_file.name+".",dir=source_file.parent,text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as stream: stream.write(candidate); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp_name,source_file)
    except Exception:
        try: os.unlink(temp_name)
        except OSError: pass
        raise
    return module_hash(parse_module(candidate))
