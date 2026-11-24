"""Tests for strict paired live-agent trace analysis."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_agent_traces", ROOT / "benchmarks" / "analyze_agent_traces.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

def record(language: str, order: int, *, model: str = "model-x",
           input_tokens: int = 100, output_tokens: int = 40,
           success: bool = True) -> dict:
    return {
        "schema_version": "aicl-agent-trace/1.0", "benchmark": "AICL-PY-100",
        "task_id": "add_01", "trial_id": "pilot-01", "language": language,
        "pair_order": order, "model_id": model, "model_snapshot": "model-x-2026-01-01",
        "tokenizer_id": "tokenizer-x", "success": success,
        "tests_passed": 5 if success else 4, "test_count": 5,
        "retry_count": 1 if not success else 0, "wall_time_ms": 200,
        "requests": [
            {"stage": "create", "input_tokens": input_tokens, "output_tokens": output_tokens, "tool_calls": 1, "latency_ms": 100},
            {"stage": "repair", "input_tokens": 10, "output_tokens": 5, "tool_calls": 2, "latency_ms": 50}]}

def test_analyze_sums_all_model_requests_and_compares_pairs() -> None:
    records = [record("python", 1), record("aicl", 2, input_tokens=80, output_tokens=40)]
    report = module.analyze(records)
    assert report["python"]["total_tokens"] == 155
    assert report["aicl"]["total_tokens"] == 135
    assert report["python"]["total_retries"] == 0
    assert report["aicl"]["stage_breakdown"]["repair"]["requests"] == 1
    assert report["paired_comparison"]["complete_pairs"] == 1
    assert report["paired_comparison"]["aggregate_token_reduction_fraction"] == pytest.approx(20 / 155, abs=1e-6)

def test_analyze_rejects_model_mismatch() -> None:
    records = [record("python", 1), record("aicl", 2, model="different")]
    with pytest.raises(ValueError, match="same model_id"):
        module.analyze(records)

def test_analyze_rejects_incomplete_pairs() -> None:
    with pytest.raises(ValueError, match="one Python and one AICL"):
        module.analyze([record("python", 1)])

def test_analyze_rejects_invalid_success_definition() -> None:
    bad = record("python", 1)
    bad["tests_passed"] = 4
    with pytest.raises(ValueError, match="success must mean all tests passed"):
        module.analyze([bad, record("aicl", 2)])

def test_analyze_rejects_duplicate_rows() -> None:
    row = record("python", 1)
    with pytest.raises(ValueError, match="duplicate trace"):
        module.analyze([row, row, record("aicl", 2)])
