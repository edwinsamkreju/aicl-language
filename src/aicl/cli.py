"""Command-line interface for the AICL 0.1 research prototype."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import AICLError
from .ir import ir_document
from .patch import apply_patch_file
from .semantics import ExecutionBudget, check_program, run_function
from .syntax import parse_module


def _read_program(path):
    try:
        return parse_module(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise AICLError("E-IO-001", f"Cannot read {path}: {exc}") from exc


def build_parser():
    parser = argparse.ArgumentParser(prog="aicl", description="AICL-C 0.1 research prototype")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="parse and type-check a module")
    check.add_argument("file")

    ir = commands.add_parser("ir", help="emit canonical typed AICL-IR as JSON")
    ir.add_argument("file")
    output = ir.add_mutually_exclusive_group()
    output.add_argument("--compact", action="store_true", help="emit whitespace-minimized canonical JSON for machine transport")
    output.add_argument("--hash-only", action="store_true", help="emit only the canonical module SHA-256")

    run = commands.add_parser("run", help="run a pure function in the reference interpreter")
    run.add_argument("file")
    run.add_argument("--function", required=True)
    run.add_argument("--args", default="[]")
    run.add_argument("--max-steps", type=int, default=100000)
    run.add_argument("--max-depth", type=int, default=128)

    manifest = commands.add_parser("py-manifest", help="emit compact signatures for selected functions in a trusted Python module")
    manifest.add_argument("module")
    manifest.add_argument("symbols", nargs="+")
    manifest.add_argument("--pretty", action="store_true", help="format the manifest for human review")

    python_run = commands.add_parser("run-python", help="run a pure AICL module through the optional CPython AST backend")
    python_run.add_argument("file")
    python_run.add_argument("--function", required=True)
    python_run.add_argument("--args", default="[]")

    patch = commands.add_parser("patch", help="apply a hash-guarded JSON or compact AICL Patch Text 0.2 patch")
    patch.add_argument("file")
    patch.add_argument("patch_file")

    agent = commands.add_parser("agent", help="run the AICL Agent Protocol 0.1 JSONL interface")
    agent.add_argument("file")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "agent":
        from .agent import run_agent
        return run_agent(args.file)

    try:
        if args.command == "py-manifest":
            from .python_interop import load_manifest
            document = load_manifest(args.module, args.symbols)
            if args.pretty:
                print(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2))
            else:
                print(json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0

        if args.command == "patch":
            digest = apply_patch_file(args.file, args.patch_file)
            print(json.dumps({"status": "patched", "module_hash": digest}, indent=2))
            return 0

        program = _read_program(args.file)
        if args.command == "check":
            check_program(program)
            print(json.dumps({
                "status": "ok",
                "version": program.version,
                "functions": len(program.functions),
                "constants": len(program.constants),
            }, indent=2))
            return 0
        if args.command == "ir":
            document = ir_document(program)
            if args.hash_only:
                print(document["module_hash"])
            elif args.compact:
                print(json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            else:
                print(json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command in {"run", "run-python"}:
            try:
                values = json.loads(args.args)
            except json.JSONDecodeError as exc:
                raise AICLError("E-CLI-001", f"--args must be a JSON array: {exc.msg}") from exc
            if not isinstance(values, list):
                raise AICLError("E-CLI-002", "--args must decode to a JSON array")
            if args.command == "run-python":
                from .backend.python import compile_program
                result = compile_program(program).run_function(args.function, values)
            else:
                result = run_function(
                    program,
                    args.function,
                    values,
                    budget=ExecutionBudget(max_steps=args.max_steps, max_depth=args.max_depth),
                )
            print(json.dumps({"result": result}, ensure_ascii=False))
            return 0
    except AICLError as exc:
        print(json.dumps({"error": exc.as_dict()}, indent=2), file=sys.stderr)
        return 2
    except (ValueError, TypeError) as exc:
        print(json.dumps({"error": {"code": "E-CLI-999", "message": str(exc)}}, indent=2), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
