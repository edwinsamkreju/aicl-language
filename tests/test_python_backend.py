from __future__ import annotations

import ast

import pytest

from aicl.backend.python import compile_program
from aicl.errors import AICLError
from aicl.semantics import run_function
from aicl.syntax import parse_module


SOURCE = """aicl 0.1
c ceiling:i64 = 10
f clamp(x:i64,lo:i64,hi:i64)->i64 !pure = max(lo,min(hi,x))
f inc(x:i64)->i64 !pure = x + 1
f mapped(xs:List[i64])->List[i64] !pure = xs |> map(inc)
f clean(xs:List[Str])->List[Str] !pure = xs |> map(trim) |> filter(not_empty) |> unique
f half(x:f64)->f64 !pure = x / 2.0
f guard(a:i64,b:i64)->bool !pure = a >= b && b != 0
f limited(x:i64)->i64 !pure = min(x,ceiling)
"""


@pytest.fixture()
def program():
    return parse_module(SOURCE)


def test_cpython_backend_matches_reference_interpreter(program):
    compiled = compile_program(program)
    cases = {
        "clamp": [[15, 0, 10], [-5, 0, 10], [4, 0, 10]],
        "inc": [[0], [-10], [99]],
        "mapped": [[[1, 2, 3]], [[]], [[-2, 5]]],
        "clean": [[[" a ", "", "b", "a", "  "]], [[]], [["x", " x "]]],
        "half": [[8.0], [3.0], [-2.0]],
        "guard": [[3, 2], [1, 2], [0, 0]],
        "limited": [[20], [-5], [10]],
    }
    for function, inputs in cases.items():
        for arguments in inputs:
            expected = run_function(program, function, arguments)
            assert compiled.run_function(function, arguments) == expected


def test_cpython_backend_generates_restricted_python_ast(program):
    compiled = compile_program(program)
    tree = ast.parse(compiled.python_source)
    assert compiled._namespace["__builtins__"] == {}
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute, ast.Subscript))
        for node in ast.walk(tree)
    )


def test_cpython_backend_checks_argument_types(program):
    compiled = compile_program(program)
    with pytest.raises(AICLError, match="Argument x must match i64"):
        compiled.run_function("clamp", [True, 0, 10])


def test_cpython_backend_rejects_unknown_functions(program):
    compiled = compile_program(program)
    with pytest.raises(AICLError, match="does not exist"):
        compiled.run_function("missing", [])


def test_cpython_backend_checks_before_lowering():
    bad = parse_module("aicl 0.1\nf bad(x:i64)->Str !pure = x\n")
    with pytest.raises(AICLError):
        compile_program(bad)
