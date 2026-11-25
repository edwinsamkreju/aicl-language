from __future__ import annotations

import sys
from types import ModuleType

import pytest

from aicl.errors import AICLError
from aicl.python_interop import build_manifest, PythonBindingRuntime


def add(left: int, right: int) -> int:
    return left + right


def label(value: str, *, prefix: str = "x") -> str:
    return prefix + value


def posonly(value: int, /, multiplier: int = 2) -> int:
    return value * multiplier


def invalid_return(value: int) -> int:
    return str(value)


@pytest.fixture()
def module(monkeypatch):
    result = ModuleType("aicl_runtime_fixture")
    result.add = add
    result.label = label
    result.posonly = posonly
    result.invalid_return = invalid_return
    monkeypatch.setitem(sys.modules, result.__name__, result)
    return result


def test_runtime_requires_explicit_capability(module):
    manifest = build_manifest(module, ["add"])
    runtime = PythonBindingRuntime.bind(manifest, grants=[])
    with pytest.raises(AICLError, match="Missing capability"):
        runtime.call("add", [2, 3])


def test_runtime_calls_only_granted_functions_and_checks_types(module):
    manifest = build_manifest(module, ["add", "label"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.add", "python:aicl_runtime_fixture.label"},
    )
    assert runtime.call("add", [2, 3]) == 5
    assert runtime.call("label", ["agent"], {"prefix": "aicl:"}) == "aicl:agent"
    with pytest.raises(AICLError, match="must match i64"):
        runtime.call("add", [True, 2])
    with pytest.raises(AICLError, match="not in the pinned manifest"):
        runtime.call("unlisted", [1])


def test_runtime_rejects_tampered_or_stale_manifest(module):
    manifest = build_manifest(module, ["add"])
    manifest["exports"][0]["return_type"] = "Str"
    with pytest.raises(AICLError, match="stale"):
        PythonBindingRuntime.bind(manifest, grants={"python:aicl_runtime_fixture.add"})


def test_runtime_rejects_unknown_grant(module):
    manifest = build_manifest(module, ["add"])
    with pytest.raises(AICLError, match="does not exist"):
        PythonBindingRuntime.bind(manifest, grants={"python:other.module.fn"})


def test_runtime_preserves_positional_only_and_optional_parameters(module):
    manifest = build_manifest(module, ["posonly"])
    runtime = PythonBindingRuntime.bind(manifest, grants={"python:aicl_runtime_fixture.posonly"})
    assert runtime.call("posonly", [4]) == 8
    assert runtime.call("posonly", [4], {"multiplier": 3}) == 12
    with pytest.raises(AICLError, match="positional-only"):
        runtime.call("posonly", [], {"value": 4})


def test_runtime_checks_host_return_type(module):
    manifest = build_manifest(module, ["invalid_return"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.invalid_return"},
    )
    with pytest.raises(AICLError, match="does not match i64"):
        runtime.call("invalid_return", [4])
