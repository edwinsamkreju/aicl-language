"""Canonical typed IR and deterministic module hashing."""
from __future__ import annotations
import hashlib,json
from typing import Any
from .semantics import check_program
from .syntax import Expr,Program

def _canonical_json(value:Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def _node(e:Expr,fn:str,path:str,type_path:str,types:dict[str,str],*,injected_first_argument=False)->dict[str,Any]:
    out={"id":f"n:{fn}:{path}","op":e.kind}
    if e.value is not None: out["value"]=e.value
    if type_path in types: out["type"]=types[type_path]
    if e.children:
        names=["left","right"] if e.kind in {"binary","pipe"} else ["operand"] if e.kind=="unary" else [f"arg{i}" for i in range(len(e.children))]
        children=[]
        for i,child in enumerate(e.children):
            child_type=f"{type_path}/arg{i+1}" if injected_first_argument else f"{type_path}/{names[i]}"
            children.append(_node(child,fn,f"{path}/{names[i]}",child_type,types,injected_first_argument=(e.kind=="pipe" and i==1 and child.kind=="call")))
        out["children"]=children
    return out

def canonical_ir(program:Program)->dict[str,Any]:
    types=check_program(program); constants=[]; functions=[]
    for c in sorted(program.constants,key=lambda x:x.name):
        constants.append({"name":c.name,"type":c.type_name,"initializer":_node(c.value,f"const:{c.name}","value",f"const:{c.name}:value",types)})
    for f in sorted(program.functions,key=lambda x:x.name):
        functions.append({"name":f.name,"parameters":[{"name":p.name,"type":p.type_name,"id":f"d:{f.name}:param:{p.name}"} for p in f.parameters],"return_type":f.return_type,"effect":f.effect,"body":_node(f.body,f.name,"body",f"fn:{f.name}:body",types)})
    return {"schema":"aicl-ir/0.1","module_version":program.version,"constants":constants,"functions":functions}

def module_hash(program:Program)->str:
    return "sha256:"+hashlib.sha256(_canonical_json(canonical_ir(program)).encode()).hexdigest()

def ir_document(program:Program)->dict[str,Any]:
    return {"module_hash":module_hash(program),"ir":canonical_ir(program)}

def canonical_json(program:Program)->str:
    return json.dumps(canonical_ir(program),ensure_ascii=False,sort_keys=True,indent=2)+"\n"
