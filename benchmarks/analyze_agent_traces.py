"""Analyze paired live-agent AICL/Python JSONL traces using provider-reported usage."""
from __future__ import annotations
import argparse, json, math, statistics, sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aicl-agent-trace/1.0"
BENCHMARK = "AICL-PY-100"
LANGUAGES = {"python", "aicl"}
STAGES = {"create", "inspect", "patch", "test", "repair", "other"}

def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value

def _validate_record(record: Any, line_number: int) -> dict[str, Any]:
    prefix = f"line {line_number}: "
    if not isinstance(record, dict):
        raise ValueError(prefix + "each JSONL record must be an object")
    required = {"schema_version", "benchmark", "task_id", "trial_id", "language",
        "pair_order", "model_id", "model_snapshot", "tokenizer_id", "experiment_config_hash", "success",
        "tests_passed", "test_count", "retry_count", "wall_time_ms", "requests"}
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError(prefix + "missing fields: " + ", ".join(missing))
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError(prefix + f"unsupported schema_version: {record['schema_version']!r}")
    if record["benchmark"] != BENCHMARK:
        raise ValueError(prefix + f"benchmark must be {BENCHMARK!r}")
    for field in ("task_id", "trial_id", "model_id", "model_snapshot", "tokenizer_id", "experiment_config_hash"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(prefix + f"{field} must be a non-empty string")
    if record["language"] not in LANGUAGES:
        raise ValueError(prefix + "language must be 'python' or 'aicl'")
    order = _integer(record["pair_order"], "pair_order", minimum=1)
    if order not in (1, 2):
        raise ValueError(prefix + "pair_order must be 1 or 2")
    if not isinstance(record["success"], bool):
        raise ValueError(prefix + "success must be a boolean")
    test_count = _integer(record["test_count"], "test_count", minimum=1)
    tests_passed = _integer(record["tests_passed"], "tests_passed")
    if tests_passed > test_count:
        raise ValueError(prefix + "tests_passed cannot exceed test_count")
    if record["success"] != (tests_passed == test_count):
        raise ValueError(prefix + "success must mean all tests passed")
    _integer(record["retry_count"], "retry_count")
    _integer(record["wall_time_ms"], "wall_time_ms")
    requests = record["requests"]
    if not isinstance(requests, list) or not requests:
        raise ValueError(prefix + "requests must be a non-empty list of model request events")
    for index, event in enumerate(requests):
        event_prefix = prefix + f"requests[{index}]: "
        if not isinstance(event, dict):
            raise ValueError(event_prefix + "must be an object")
        if event.get("stage") not in STAGES:
            raise ValueError(event_prefix + "stage must be one of " + ", ".join(sorted(STAGES)))
        for field in ("input_tokens", "output_tokens", "tool_calls"):
            _integer(event.get(field), event_prefix + field)
        if "latency_ms" in event:
            _integer(event["latency_ms"], event_prefix + "latency_ms")
    return record

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            records.append(_validate_record(value, line_number))
    if not records:
        raise ValueError("trace file contains no records")
    return records

def _run_totals(record: dict[str, Any]) -> dict[str, Any]:
    events = record["requests"]
    input_tokens = sum(e["input_tokens"] for e in events)
    output_tokens = sum(e["output_tokens"] for e in events)
    tools = sum(e["tool_calls"] for e in events)
    stages: dict[str, dict[str, int]] = {}
    for event in events:
        stage = stages.setdefault(event["stage"], {
            "requests": 0, "input_tokens": 0, "output_tokens": 0, "tool_calls": 0})
        stage["requests"] += 1
        stage["input_tokens"] += event["input_tokens"]
        stage["output_tokens"] += event["output_tokens"]
        stage["tool_calls"] += event["tool_calls"]
    return {"input_tokens": input_tokens, "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens, "tool_calls": tools,
        "request_count": len(events), "stages": stages}

def _language_summary(records: list[dict[str, Any]], language: str,
                      input_rate: float | None, output_rate: float | None) -> dict[str, Any]:
    selected = [r for r in records if r["language"] == language]
    runs = [_run_totals(r) for r in selected]
    totals = [r["total_tokens"] for r in runs]
    succeeded = sum(1 for r in selected if r["success"])
    summary: dict[str, Any] = {
        "runs": len(selected), "successful_runs": succeeded,
        "success_rate": round(succeeded / len(selected), 6) if selected else None,
        "total_input_tokens": sum(r["input_tokens"] for r in runs),
        "total_output_tokens": sum(r["output_tokens"] for r in runs),
        "total_tokens": sum(totals),
        "mean_tokens_per_run": round(statistics.mean(totals), 3) if totals else None,
        "median_tokens_per_run": statistics.median(totals) if totals else None,
        "mean_tokens_per_successful_run": (
            round(statistics.mean([v for v, r in zip(totals, selected) if r["success"]]), 3)
            if succeeded else None),
        "total_requests": sum(r["request_count"] for r in runs),
        "total_tool_calls": sum(r["tool_calls"] for r in runs),
        "total_retries": sum(r["retry_count"] for r in selected),
        "mean_retries_per_run": round(statistics.mean([r["retry_count"] for r in selected]), 3) if selected else None,
        "mean_wall_time_ms": round(statistics.mean([r["wall_time_ms"] for r in selected]), 3) if selected else None}
    merged: dict[str, dict[str, int]] = {}
    for run in runs:
        for name, values in run["stages"].items():
            stage = merged.setdefault(name, {k: 0 for k in ("requests", "input_tokens", "output_tokens", "tool_calls")})
            for key, value in values.items():
                stage[key] += value
    summary["stage_breakdown"] = merged
    if input_rate is not None and output_rate is not None:
        summary["estimated_cost_usd"] = round(
            (summary["total_input_tokens"] * input_rate + summary["total_output_tokens"] * output_rate) / 1_000_000, 8)
    return summary

def analyze(records: list[dict[str, Any]], input_rate: float | None = None,
            output_rate: float | None = None) -> dict[str, Any]:
    records = [_validate_record(record, index) for index, record in enumerate(records, start=1)]
    if (input_rate is None) != (output_rate is None):
        raise ValueError("provide both input and output token rates, or neither")
    for rate in (input_rate, output_rate):
        if rate is not None and (not math.isfinite(rate) or rate < 0):
            raise ValueError("token rates must be finite non-negative USD per million tokens")
    identities = {(r["model_id"], r["model_snapshot"], r["tokenizer_id"], r["experiment_config_hash"]) for r in records}
    if len(identities) != 1:
        raise ValueError("all traces must use the same model_id, model_snapshot, tokenizer_id, and experiment_config_hash")
    pairs: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    seen = set()
    for record in records:
        key = (record["task_id"], record["trial_id"], record["language"])
        if key in seen:
            raise ValueError(f"duplicate trace for task={key[0]!r}, trial={key[1]!r}, language={key[2]!r}")
        seen.add(key)
        pairs[(record["task_id"], record["trial_id"])][record["language"]] = record
    incomplete = [key for key, pair in pairs.items() if set(pair) != LANGUAGES]
    if incomplete:
        preview = ", ".join(f"{task}/{trial}" for task, trial in incomplete[:5])
        raise ValueError("every task/trial needs one Python and one AICL run; incomplete pairs: " + preview)
    for key, pair in pairs.items():
        if {r["pair_order"] for r in pair.values()} != {1, 2}:
            raise ValueError(f"paired task {key[0]!r}/{key[1]!r} must record pair_order 1 and 2")
    py = _language_summary(records, "python", input_rate, output_rate)
    aicl = _language_summary(records, "aicl", input_rate, output_rate)
    reductions = []
    both_success_reductions = []
    aicl_lower = 0
    for pair in pairs.values():
        p, a = pair["python"], pair["aicl"]
        pt, at = _run_totals(p)["total_tokens"], _run_totals(a)["total_tokens"]
        if pt:
            reduction = (pt - at) / pt
            reductions.append(reduction)
            if at < pt:
                aicl_lower += 1
            if p["success"] and a["success"]:
                both_success_reductions.append(reduction)
    paired = {"complete_pairs": len(pairs),
        "both_successful_pairs": sum(1 for p in pairs.values() if p["python"]["success"] and p["aicl"]["success"]),
        "aicl_lower_token_pairs": aicl_lower,
        "aggregate_token_reduction_fraction": round((py["total_tokens"] - aicl["total_tokens"]) / py["total_tokens"], 6) if py["total_tokens"] else None,
        "mean_pairwise_token_reduction_fraction": round(statistics.mean(reductions), 6) if reductions else None,
        "mean_pairwise_token_reduction_when_both_succeed": round(statistics.mean(both_success_reductions), 6) if both_success_reductions else None}
    per_pair = []
    for (task_id, trial_id), pair in sorted(pairs.items()):
        p, a = pair["python"], pair["aicl"]
        pt, at = _run_totals(p), _run_totals(a)
        per_pair.append({
            "task_id": task_id, "trial_id": trial_id,
            "first_language": "python" if p["pair_order"] == 1 else "aicl",
            "python": {"success": p["success"], "tests_passed": p["tests_passed"],
                "test_count": p["test_count"], "input_tokens": pt["input_tokens"],
                "output_tokens": pt["output_tokens"], "total_tokens": pt["total_tokens"],
                "retry_count": p["retry_count"], "tool_calls": pt["tool_calls"],
                "wall_time_ms": p["wall_time_ms"]},
            "aicl": {"success": a["success"], "tests_passed": a["tests_passed"],
                "test_count": a["test_count"], "input_tokens": at["input_tokens"],
                "output_tokens": at["output_tokens"], "total_tokens": at["total_tokens"],
                "retry_count": a["retry_count"], "tool_calls": at["tool_calls"],
                "wall_time_ms": a["wall_time_ms"]},
            "aicl_token_delta": pt["total_tokens"] - at["total_tokens"],
            "aicl_token_reduction_fraction": (
                round((pt["total_tokens"] - at["total_tokens"]) / pt["total_tokens"], 6)
                if pt["total_tokens"] else None)})
    identity = next(iter(identities))
    return {"schema_version": "aicl-agent-benchmark-report/1.0", "benchmark": BENCHMARK,
        "model": {"model_id": identity[0], "model_snapshot": identity[1],
                  "tokenizer_id": identity[2], "experiment_config_hash": identity[3]},
        "python": py, "aicl": aicl, "paired_comparison": paired, "per_pair_results": per_pair,
        "notes": [
            "Token usage is summed from provider-reported usage for every model request in each complete run, including repair and retry requests.",
            "A paired reduction is positive when AICL used fewer tokens than Python.",
            "The report is only as reliable as the imported request traces; retain provider usage receipts and experiment configuration.",
            "Optional cost estimates use user-supplied USD-per-million input and output token rates; prices are not inferred."]}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSONL file using the AICL live-agent trace schema")
    parser.add_argument("--output", type=Path, help="Optional output JSON path (report is also printed)")
    parser.add_argument("--input-rate-per-million", type=float)
    parser.add_argument("--output-rate-per-million", type=float)
    args = parser.parse_args()
    try:
        records = load_jsonl(args.input)
        result = analyze(records, args.input_rate_per_million, args.output_rate_per_million)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
