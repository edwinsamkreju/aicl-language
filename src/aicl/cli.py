"""Command-line interface for the AICL 0.1 research prototype."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .errors import AICLError
from .ir import ir_document
from .patch import apply_patch_file
from .semantics import check_program,run_function,ExecutionBudget
from .syntax import parse_module

def _read_program(path):
    try: return parse_module(Path(path).read_text(encoding="utf-8"))
    except OSError as exc: raise AICLError("E-IO-001",f"Cannot read {path}: {exc}") from exc

def build_parser():
    parser=argparse.ArgumentParser(prog="aicl",description="AICL-C 0.1 research prototype")
    commands=parser.add_subparsers(dest="command",required=True)
    check=commands.add_parser("check",help="parse and type-check a module"); check.add_argument("file")
    ir=commands.add_parser("ir",help="emit canonical typed AICL-IR as JSON"); ir.add_argument("file")
    run=commands.add_parser("run",help="run a pure function in the reference interpreter")
    run.add_argument("file"); run.add_argument("--function",required=True); run.add_argument("--args",default="[]")
    run.add_argument("--max-steps",type=int,default=100000); run.add_argument("--max-depth",type=int,default=128)
    patch=commands.add_parser("patch",help="apply a hash-guarded JSON or compact AICL Patch Text 0.2 patch")
    patch.add_argument("file"); patch.add_argument("patch_file")
    return parser

def main(argv=None):
    args=build_parser().parse_args(argv)
    try:
        if args.command=="patch":
            h=apply_patch_file(args.file,args.patch_file)
            print(json.dumps({"status":"patched","module_hash":h},indent=2)); return 0
        program=_read_program(args.file)
        if args.command=="check":
            check_program(program)
            print(json.dumps({"status":"ok","version":program.version,"functions":len(program.functions),"constants":len(program.constants)},indent=2)); return 0
        if args.command=="ir": print(json.dumps(ir_document(program),indent=2,ensure_ascii=False)); return 0
        if args.command=="run":
            try: values=json.loads(args.args)
            except json.JSONDecodeError as exc: raise AICLError("E-CLI-001",f"--args must be a JSON array: {exc.msg}") from exc
            if not isinstance(values,list): raise AICLError("E-CLI-002","--args must decode to a JSON array")
            result=run_function(program,args.function,values,budget=ExecutionBudget(max_steps=args.max_steps,max_depth=args.max_depth))
            print(json.dumps({"result":result},ensure_ascii=False)); return 0
    except AICLError as exc:
        print(json.dumps({"error":exc.as_dict()},indent=2),file=sys.stderr); return 2
    except (ValueError,TypeError) as exc:
        print(json.dumps({"error":{"code":"E-CLI-999","message":str(exc)}},indent=2),file=sys.stderr); return 2
    return 1
if __name__=="__main__": raise SystemExit(main())
