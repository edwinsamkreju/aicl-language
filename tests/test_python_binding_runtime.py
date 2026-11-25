from __future__ import annotations

import sys
from types import ModuleType

import pytest

from aicl.errors import AICLError
from aicl.python_interop import build_manifest, PythonBindingRuntime


def add(left: int, right: int) -> int:
    return left + right


def passthrough(value):
    return value


def label(value: str, *, prefix: str = "x") -> str:
    return prefix + value


def posonly(value: int, /, multiplier: int = 2) -> int:
    return value * multiplier


def invalid_return(value: int) -> int:
    return str(value)


def mutate(values: list[int]) -> list[int]:
    values.append(9)
    return values


def echo_nested(values: list[list[int]]) -> list[list[int]]:
    return values


def make_awaitable(value: int) -> int:
    async def result():
        return value
    return result()


@pytest.fixture()
def module(monkeypatch):
    result = ModuleType("aicl_runtime_fixture")
    result.add = add
    result.passthrough = passthrough
    result.label = label
    result.posonly = posonly
    result.invalid_return = invalid_return
    result.mutate = mutate
    result.echo_nested = echo_nested
    result.make_awaitable = make_awaitable
    monkeypatch.setitem(sys.modules, result.__name__, result)
    return result


def test_runtime_requires_explicit_capability(module):
    manifest = build_manifest(module, ["add", "label"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.add"},
    )
    assert runtime.call("add", [2, 3]) == 5
    with pytest.raises(AICLError, match="Missing capability"):
        runtime.call("label", ["blocked"])
    with pytest.raises(AICLError, match="At least one explicit"):
        PythonBindingRuntime.bind(manifest, grants=[])


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
    with pytest.raises(AICLError, match="must match i64"):
        runtime.call("invalid_return", [4])

def test_runtime_copies_mutable_lists_across_the_host_boundary(module):
    manifest = build_manifest(module, ["mutate"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.mutate"},
    )
    values = [1, 2]
    result = runtime.call("mutate", [values])
    assert values == [1, 2]
    assert result == [1, 2, 9]
    assert result is not values


def test_runtime_bounds_list_size_and_nesting(module):
    manifest = build_manifest(module, ["mutate"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.mutate"},
    )
    with pytest.raises(AICLError, match="10000-item list limit"):
        runtime.call("mutate", [[0] * 10_001])



def test_runtime_revalidates_and_invokes_explicit_unannotated_function(module):
    declaration = {
        "passthrough": {
            "parameters": [{
                "name": "value",
                "type": "i64",
                "kind": "positional_or_keyword",
                "required": True,
            }],
            "return_type": "i64",
        }
    }
    manifest = build_manifest(module, ["passthrough"], declarations=declaration)
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.passthrough"},
    )
    assert runtime.call("passthrough", [42]) == 42


def test_runtime_bounds_total_nested_list_items(module):
    manifest = build_manifest(module, ["echo_nested"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.echo_nested"},
    )
    with pytest.raises(AICLError, match="100000-item aggregate value limit"):
        runtime.call("echo_nested", [[index for index in range(10_000)] for _ in range(11)])



def test_runtime_rejects_awaitable_host_results(module):
    manifest = build_manifest(module, ["make_awaitable"])
    runtime = PythonBindingRuntime.bind(
        manifest,
        grants={"python:aicl_runtime_fixture.make_awaitable"},
    )
    with pytest.raises(AICLError, match="Awaitable host-call results"):
        runtime.call("make_awaitable", [1])
