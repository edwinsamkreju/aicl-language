"""Run the 100-task Python/AICL equivalence and optional tokenizer benchmark."""
from __future__ import annotations
import argparse, json, platform, runpy, time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "benchmarks" / "tasks" / "paired_suite.json"

def _load_tasks(path: Path) -> dict[str, Any]:
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        build_suite = runpy.run_path(str(ROOT / "benchmarks" / "generate_suite.py"))["build_suite"]
        data = {"suite": "AICL-PY-100", "suite_version": "1.0", "task_count": 100,
                "case_count_per_task": 5, "tasks": build_suite()}
    if data.get("task_count") != len(data.get("tasks", [])):
        raise ValueError("Suite task_count does not match task records")
    if len(data["tasks"]) != 100:
        raise ValueError(f"Expected exactly 100 tasks; found {len(data['tasks'])}")
    ids = [t["id"] for t in data["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Task IDs must be unique")
    return data

def _python_namespace(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__builtins__": {
        "min": min, "max": max, "abs": abs, "list": list, "dict": dict,
        "int": int, "bool": bool, "str": str}}
    source = "\n".join(t["python_source"] for t in tasks)
    exec(compile(source, "<paired-benchmark-python>", "exec"), namespace)
    return namespace

def _run_correctness(tasks: list[dict[str, Any]], namespace: dict[str, Any],
                     interpreter: Any) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    cases = 0
    for task in tasks:
        py_fn = namespace[task["id"]]
        for case_index, case in enumerate(task["cases"]):
            args = case["args"]
            py_value = py_fn(*args)
            aicl_value = interpreter.call(task["id"], args)
            cases += 1
            if type(py_value) is not type(aicl_value) or py_value != aicl_value:
                mismatches.append({"task": task["id"], "case_index": case_index,
                                   "args": args, "python": py_value, "aicl": aicl_value})
    return {"cases_run": cases, "mismatch_count": len(mismatches), "mismatches": mismatches[:20]}

def _time_runs(tasks: list[dict[str, Any]], namespace: dict[str, Any],
               interpreter: Any, repeats: int) -> dict[str, Any]:
    calls = [(task, case["args"]) for task in tasks for case in task["cases"]]
    start = time.perf_counter()
    for _ in range(repeats):
        for task, args in calls:
            namespace[task["id"]](*args)
    python_seconds = time.perf_counter() - start
    start = time.perf_counter()
    for _ in range(repeats):
        for task, args in calls:
            interpreter.call(task["id"], args)
    aicl_seconds = time.perf_counter() - start
    total_calls = len(calls) * repeats
    return {
        "repeats_per_case_set": repeats, "calls_per_language": total_calls,
        "python_seconds": round(python_seconds, 6),
        "aicl_reference_interpreter_seconds": round(aicl_seconds, 6),
        "python_microseconds_per_call": round(python_seconds * 1_000_000 / total_calls, 3),
        "aicl_microseconds_per_call": round(aicl_seconds * 1_000_000 / total_calls, 3),
        "interpretation": "Diagnostic only: compares CPython function calls with this Python-hosted AICL reference interpreter; not a native-language or compiler performance comparison."}

def _token_counts(tasks: list[dict[str, Any]], encoding_name: str) -> dict[str, Any]:
    py_source = "\n".join(t["python_source"] for t in tasks)
    aicl_source = "aicl 0.1\n" + "\n".join(t["aicl_source"] for t in tasks) + "\n"
    py_chars, aicl_chars = len(py_source), len(aicl_source)
    chars = {"python_source_characters": py_chars, "aicl_source_characters": aicl_chars,
             "source_character_reduction_fraction": round((py_chars - aicl_chars) / py_chars, 6) if py_chars else 0}
    try:
        import tiktoken
    except ImportError:
        return {"available": False, "reason": "tiktoken is not installed; install with python -m pip install -e '.[bench]'.",
                **chars, "python_source_tokens": None, "aicl_source_tokens": None,
                "shared_task_prompt_tokens": None, "python_prompt_plus_source_tokens": None,
                "aicl_prompt_plus_source_tokens": None, "edit_debug_retry_tokens": None,
                "end_to_end_model_workflow_tokens": None}
    encoding = tiktoken.get_encoding(encoding_name)
    prompts = "\n".join("Implement this pure function: " + t["description"] +
        " Parameters: " + json.dumps(t["parameters"], separators=(",", ":")) +
        " Return type: " + t["return_type"] + "." for t in tasks)
    py_tokens, aicl_tokens = len(encoding.encode(py_source)), len(encoding.encode(aicl_source))
    prompt_tokens = len(encoding.encode(prompts))
    return {"available": True, **chars, "tokenizer": "tiktoken", "encoding": encoding_name,
            "python_source_tokens": py_tokens, "aicl_source_tokens": aicl_tokens,
            "source_token_reduction_fraction": round((py_tokens - aicl_tokens) / py_tokens, 6) if py_tokens else 0,
            "shared_task_prompt_tokens": prompt_tokens,
            "python_prompt_plus_source_tokens": prompt_tokens + py_tokens,
            "aicl_prompt_plus_source_tokens": prompt_tokens + aicl_tokens,
            "edit_debug_retry_tokens": None, "end_to_end_model_workflow_tokens": None,
            "scope_note": "Counts a deterministic task-description prompt corpus plus checked-in program sources. Not observed model input/output, tool, edit, repair, or retry usage."}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--encoding", default="cl100k_base")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    data = _load_tasks(args.suite)
    tasks = data["tasks"]
    try:
        from aicl.semantics import Interpreter
        from aicl.syntax import parse_module
    except ImportError as exc:
        raise SystemExit("Could not import AICL. Install the project first: python -m pip install -e .") from exc
    aicl_source = "aicl 0.1\n" + "\n".join(t["aicl_source"] for t in tasks) + "\n"
    parse_start = time.perf_counter()
    program = parse_module(aicl_source)
    parse_seconds = time.perf_counter() - parse_start
    interpreter_start = time.perf_counter()
    interpreter = Interpreter(program)
    typecheck_seconds = time.perf_counter() - interpreter_start
    namespace = _python_namespace(tasks)
    correctness = _run_correctness(tasks, namespace, interpreter)
    timing = _time_runs(tasks, namespace, interpreter, args.repeats)
    result = {
        "benchmark": data["suite"], "suite_version": data["suite_version"],
        "task_count": len(tasks), "case_count_per_task": data["case_count_per_task"],
        "correctness": correctness,
        "aicl_frontend_setup": {"parse_seconds": round(parse_seconds, 6),
            "interpreter_initialization_and_typecheck_seconds": round(typecheck_seconds, 6)},
        "runtime": timing, "tokens": _token_counts(tasks, args.encoding),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "limitations": [
            "The corpus only covers the implemented AICL-C 0.1 subset and is not representative of arbitrary software projects.",
            "Each task has five fixed test cases; passing them is not proof of semantic equivalence for all inputs.",
            "No model is called, so actual completion tokens, tool-call tokens, edit iterations, debugging, retries, and full workflow cost remain unmeasured.",
            "Token counts include checked-in source and a deterministic task prompt corpus only; shared prompts are identical on both sides.",
            "Runtime compares CPython with a Python-hosted reference interpreter and is not a native runtime benchmark."]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if correctness["mismatch_count"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
