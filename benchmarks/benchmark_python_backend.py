"""Measure AICL CPython backend setup and warmed execution separately."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

from aicl.backend.python import compile_program
from aicl.semantics import ExecutionBudget, Interpreter, run_function
from aicl.syntax import parse_module


def _timed_samples(operation: Callable[[], object], repeats: int) -> list[float]:
    samples = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        operation()
        samples.append((time.perf_counter_ns() - started) / 1_000)
    return samples


def _measure_calls(operation: Callable[[], object], iterations: int, repeats: int) -> dict[str, float]:
    for _ in range(min(iterations, 1_000)):
        operation()
    samples = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed = time.perf_counter_ns() - started
        samples.append(elapsed / iterations / 1_000)
    return {
        "median_us_per_call": statistics.median(samples),
        "min_us_per_call": min(samples),
        "max_us_per_call": max(samples),
        "median_calls_per_second": 1_000_000 / statistics.median(samples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="examples/clamp.aicl")
    parser.add_argument("--function", default="clamp")
    parser.add_argument("--args", default="[15, 0, 10]")
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    if args.iterations < 1 or args.repeats < 3:
        parser.error("--iterations must be positive and --repeats must be at least 3")
    try:
        call_args = json.loads(args.args)
    except json.JSONDecodeError as exc:
        parser.error(f"--args must be a JSON array: {exc.msg}")
    if not isinstance(call_args, list):
        parser.error("--args must decode to a JSON array")

    source = Path(args.file).read_text(encoding="utf-8")
    parse_samples = _timed_samples(lambda: parse_module(source), args.repeats)
    program = parse_module(source)

    compile_samples = _timed_samples(lambda: compile_program(program), args.repeats)
    compiled = compile_program(program)
    interpreter_setup_samples = _timed_samples(lambda: Interpreter(program), args.repeats)
    interpreter = Interpreter(
        program,
        budget=ExecutionBudget(max_steps=(args.iterations * args.repeats + 1_000) * 100),
    )

    expected = run_function(program, args.function, call_args)
    compiled_result = compiled.run_function(args.function, call_args)
    if expected != compiled_result:
        raise SystemExit("Reference and CPython backend results differ")

    reference_warm = lambda: interpreter.call(args.function, call_args)
    cpython_raw = lambda: compiled._namespace[f"_f_{args.function}"](*call_args)
    cpython_checked = lambda: compiled.run_function(args.function, call_args)
    reference_public = lambda: run_function(program, args.function, call_args)

    measurements = {
        "reference_interpreter_warm": _measure_calls(reference_warm, args.iterations, args.repeats),
        "cpython_backend_raw": _measure_calls(cpython_raw, args.iterations, args.repeats),
        "cpython_backend_checked": _measure_calls(cpython_checked, args.iterations, args.repeats),
        "reference_public_run_function": _measure_calls(
            reference_public, max(100, args.iterations // 100), args.repeats
        ),
    }
    result = {
        "benchmark": "aicl-python-backend/0.1",
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": sys.platform,
        "source_file": args.file,
        "function": args.function,
        "iterations_per_repeat": args.iterations,
        "repeats": args.repeats,
        "setup_median_us": {
            "parse": statistics.median(parse_samples),
            "cpython_backend_compile_including_typecheck": statistics.median(compile_samples),
            "reference_interpreter_init_including_typecheck": statistics.median(interpreter_setup_samples),
        },
        "warmed_execution": measurements,
        "semantic_parity": True,
        "notes": [
            "Compile and interpreter setup costs are reported separately from warmed calls.",
            "reference_interpreter_warm and cpython_backend_raw compare their internal warmed call paths.",
            "cpython_backend_checked includes argument and result validation; raw does not.",
            "reference_public_run_function includes interpreter construction and type-check setup per invocation.",
            "This microbenchmark is diagnostic, not a representative application or AI-agent workflow result.",
        ],
    }
    output = json.dumps(result, sort_keys=True, separators=(",", ":"))
    print(output)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
