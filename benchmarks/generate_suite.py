"""Generate the deterministic 100-task paired Python/AICL benchmark corpus."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "tasks" / "paired_suite.json"

def make_task(task_id: str, description: str, parameter: str, parameter_type: str,
              return_type: str, py_type: str, py_expr: str, aicl_expr: str,
              cases: list[list[object]]) -> dict[str, object]:
    py_return = {"i64": "int", "bool": "bool", "Str": "str", "List[i64]": "list[int]"}[return_type]
    py_source = f"def {task_id}({parameter}: {py_type}) -> {py_return}:\n    return {py_expr}\n"
    aicl_source = f"f {task_id}({parameter}:{parameter_type})->{return_type} !pure = {aicl_expr}"
    return {"id": task_id, "description": description,
            "parameters": [{"name": parameter, "type": parameter_type}],
            "return_type": return_type, "python_source": py_source,
            "aicl_source": aicl_source, "cases": [{"args": case} for case in cases]}

def build_suite() -> list[dict[str, object]]:
    integers = [[-17], [-1], [0], [1], [23]]
    strings = [[""], ["alpha"], ["  spaced text  "], ["café"], [" 東京 "]]
    lists = [[], [1], [1, 1, 2], [3, -1, 3, 0], list(range(20))]
    tasks: list[dict[str, object]] = []
    suffixes = ["!", "?", "-x", "_v", " done", "✓", "::", "/", " café", "🙂"]
    for i in range(1, 11):
        k = i
        tasks.append(make_task(f"add_{i:02d}", f"Return the integer input plus {k}.", "x", "i64", "i64", "int", f"x + {k}", f"x+{k}", integers))
        tasks.append(make_task(f"subtract_{i:02d}", f"Return the integer input minus {k}.", "x", "i64", "i64", "int", f"x - {k}", f"x-{k}", integers))
        tasks.append(make_task(f"multiply_{i:02d}", f"Return the integer input multiplied by {k}.", "x", "i64", "i64", "int", f"x * {k}", f"x*{k}", integers))
        tasks.append(make_task(f"minimum_{i:02d}", f"Return the smaller of the integer input and {k}.", "x", "i64", "i64", "int", f"min(x, {k})", f"min(x,{k})", integers))
        tasks.append(make_task(f"maximum_{i:02d}", f"Return the larger of the integer input and {k}.", "x", "i64", "i64", "int", f"max(x, {k})", f"max(x,{k})", integers))
        tasks.append(make_task(f"absolute_delta_{i:02d}", f"Return the absolute difference between the integer input and {k}.", "x", "i64", "i64", "int", f"abs(x - {k})", f"abs(x-{k})", integers))
        tasks.append(make_task(f"greater_than_{i:02d}", f"Return whether the integer input is greater than {k}.", "x", "i64", "bool", "int", f"x > {k}", f"x>{k}", integers))
        suffix = suffixes[i - 1]
        quoted = json.dumps(suffix, ensure_ascii=False)
        tasks.append(make_task(f"append_suffix_{i:02d}", f"Append the exact suffix {suffix!r} to the input string.", "s", "Str", "Str", "str", f"s + {quoted}", f"s+{quoted}", strings))
        tasks.append(make_task(f"trim_string_{i:02d}", f"Remove leading and trailing whitespace from the input string (case {i}).", "s", "Str", "Str", "str", "s.strip()", "trim(s)", strings))
        tasks.append(make_task(f"unique_list_{i:02d}", f"Remove duplicate integers while preserving their first-occurrence order (case {i}).", "xs", "List[i64]", "List[i64]", "list[int]", "list(dict.fromkeys(xs))", "unique(xs)", [[v] for v in lists]))
    assert len(tasks) == 100
    return tasks

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"suite": "AICL-PY-100", "suite_version": "1.0", "task_count": 100,
               "case_count_per_task": 5,
               "scope": "Pure functions expressible in the current AICL-C 0.1 prototype.",
               "tasks": build_suite()}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['tasks'])} paired tasks to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
