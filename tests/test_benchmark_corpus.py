"""Structural checks for the deterministic 100-task paired benchmark corpus."""
from __future__ import annotations
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_paired_suite_has_one_hundred_unique_tasks_and_five_cases_each() -> None:
    build_suite = runpy.run_path(str(ROOT / "benchmarks" / "generate_suite.py"))["build_suite"]
    tasks = build_suite()
    assert len(tasks) == 100
    assert len({task["id"] for task in tasks}) == 100
    assert all(len(task["cases"]) == 5 for task in tasks)
    assert sum(len(task["cases"]) for task in tasks) == 500

def test_each_task_contains_both_language_forms_and_shared_test_inputs() -> None:
    build_suite = runpy.run_path(str(ROOT / "benchmarks" / "generate_suite.py"))["build_suite"]
    for task in build_suite():
        assert task["python_source"].startswith("def ")
        assert task["aicl_source"].startswith("f ")
        assert task["description"].strip()
        assert len(task["parameters"]) == 1
        assert task["return_type"]
        assert all(isinstance(case["args"], list) for case in task["cases"])
