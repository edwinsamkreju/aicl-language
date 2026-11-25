"""Lower checked AICL expressions to Python AST and execute with CPython."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from types import CodeType
from typing import Any, Sequence

from ...errors import AICLError
from ...semantics import check_program
from ...syntax import Expr, Program

_MAX_COLLECTION_ITEMS = 10_000


def _bounded(values: list[Any], operation: str) -> None:
    if len(values) > _MAX_COLLECTION_ITEMS:
        raise AICLError("E-PYBACKEND-010", f"{operation} input exceeds the {_MAX_COLLECTION_ITEMS}-item prototype limit")


def _aicl_trim(value: str) -> str:
    return value.strip()


def _aicl_not_empty(value: str) -> bool:
    return bool(value.strip())


def _aicl_unique(values: list[Any]) -> list[Any]:
    _bounded(values, "unique")
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _aicl_map(values: list[Any], callback: Any) -> list[Any]:
    _bounded(values, "map")
    return [callback(value) for value in values]


def _aicl_filter(values: list[Any], callback: Any) -> list[Any]:
    _bounded(values, "filter")
    return [value for value in values if callback(value)]


_CALL_TARGETS = {
    "min": "min", "max": "max", "abs": "_aicl_abs", "len": "_aicl_len",
    "trim": "_aicl_trim", "not_empty": "_aicl_not_empty",
    "unique": "_aicl_unique", "map": "_aicl_map", "filter": "_aicl_filter",
}
_VALUE_TARGETS = {"trim": "_aicl_trim", "not_empty": "_aicl_not_empty"}


def _name(identifier: str) -> ast.Name:
    return ast.Name(id=identifier, ctx=ast.Load())


def _call(identifier: str, args: list[ast.expr]) -> ast.Call:
    return ast.Call(func=_name(identifier), args=args, keywords=[])


def _lower_expr(expression: Expr, *, locals_map: dict[str, str], constants: set[str], functions: set[str]) -> ast.expr:
    kind = expression.kind
    if kind == "literal":
        return ast.Constant(value=expression.value)
    if kind == "name":
        value = str(expression.value)
        if value in locals_map:
            return _name(locals_map[value])
        if value in constants:
            return _name(f"_c_{value}")
        if value in functions:
            return _name(f"_f_{value}")
        if value in _VALUE_TARGETS:
            return _name(_VALUE_TARGETS[value])
        raise AICLError("E-PYBACKEND-001", f"Unsupported value reference {value!r}")
    if kind == "unary":
        operand = _lower_expr(expression.children[0], locals_map=locals_map, constants=constants, functions=functions)
        operator = ast.USub() if expression.value == "-" else ast.Not()
        return ast.UnaryOp(op=operator, operand=operand)
    if kind == "binary":
        left, right = expression.children
        lhs = _lower_expr(left, locals_map=locals_map, constants=constants, functions=functions)
        rhs = _lower_expr(right, locals_map=locals_map, constants=constants, functions=functions)
        binary_ops = {"+": ast.Add, "-": ast.Sub, "*": ast.Mult, "/": ast.Div, "%": ast.Mod}
        compare_ops = {"==": ast.Eq, "!=": ast.NotEq, "<": ast.Lt, "<=": ast.LtE, ">": ast.Gt, ">=": ast.GtE}
        operator = expression.value
        if operator in binary_ops:
            return ast.BinOp(left=lhs, op=binary_ops[operator](), right=rhs)
        if operator in compare_ops:
            return ast.Compare(left=lhs, ops=[compare_ops[operator]()], comparators=[rhs])
        if operator == "&&":
            return ast.BoolOp(op=ast.And(), values=[lhs, rhs])
        if operator == "||":
            return ast.BoolOp(op=ast.Or(), values=[lhs, rhs])
        raise AICLError("E-PYBACKEND-002", f"Unsupported binary operator {operator!r}")
    if kind == "call":
        target = _CALL_TARGETS.get(str(expression.value), f"_f_{expression.value}")
        args = [_lower_expr(arg, locals_map=locals_map, constants=constants, functions=functions) for arg in expression.children]
        return _call(target, args)
    if kind == "pipe":
        left, right = expression.children
        target_name = str(right.value)
        target = _CALL_TARGETS.get(target_name, f"_f_{target_name}")
        args = [_lower_expr(left, locals_map=locals_map, constants=constants, functions=functions)]
        if right.kind == "call":
            args.extend(_lower_expr(arg, locals_map=locals_map, constants=constants, functions=functions) for arg in right.children)
        elif right.kind != "name":
            raise AICLError("E-PYBACKEND-003", "Invalid AICL pipeline target")
        return _call(target, args)
    raise AICLError("E-PYBACKEND-004", f"Unsupported AICL expression node {kind!r}")


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "Str":
        return isinstance(value, str)
    if type_name == "i64":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "f64":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name.startswith("List[") and type_name.endswith("]"):
        item_type = type_name[5:-1]
        return isinstance(value, list) and all(_matches_type(item, item_type) for item in value)
    return False


@dataclass
class CompiledProgram:
    """Compiled AICL module with a small, explicit CPython global namespace."""
    _namespace: dict[str, Any]
    _code: CodeType
    _functions: dict[str, Any]
    python_source: str

    def run_function(self, name: str, arguments: Sequence[Any]) -> Any:
        function = self._functions.get(name)
        if function is None:
            raise AICLError("E-PYBACKEND-005", f"Function {name!r} does not exist")
        if not isinstance(arguments, (list, tuple)):
            raise AICLError("E-PYBACKEND-006", "Arguments must be a list or tuple")
        if len(arguments) != len(function.parameters):
            raise AICLError("E-PYBACKEND-007", f"{name} expects {len(function.parameters)} arguments, received {len(arguments)}")
        for parameter, value in zip(function.parameters, arguments):
            if not _matches_type(value, parameter.type_name):
                raise AICLError("E-PYBACKEND-008", f"Argument {parameter.name} must match {parameter.type_name}")
        try:
            result = self._namespace[f"_f_{name}"](*arguments)
        except AICLError:
            raise
        except Exception as exc:
            raise AICLError("E-PYBACKEND-009", f"CPython execution failed: {type(exc).__name__}: {exc}") from exc
        if not _matches_type(result, function.return_type):
            raise AICLError("E-PYBACKEND-011", f"Runtime result for {name} did not match declared type {function.return_type}")
        return result


def compile_program(program: Program) -> CompiledProgram:
    """Type-check, lower to Python AST, and compile an AICL module with CPython."""
    check_program(program)
    function_names = {function.name for function in program.functions}
    all_constant_names = {constant.name for constant in program.constants}
    module_body: list[ast.stmt] = []
    for function in program.functions:
        local_names = {parameter.name: f"_p{index}" for index, parameter in enumerate(function.parameters)}
        args = ast.arguments(posonlyargs=[], args=[ast.arg(arg=local_names[p.name]) for p in function.parameters], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
        body = _lower_expr(function.body, locals_map=local_names, constants=all_constant_names, functions=function_names)
        module_body.append(ast.FunctionDef(name=f"_f_{function.name}", args=args, body=[ast.Return(value=body)], decorator_list=[], returns=None, type_comment=None))

    prior_constants: set[str] = set()
    for constant in program.constants:
        value = _lower_expr(constant.value, locals_map={name: f"_c_{name}" for name in prior_constants}, constants=prior_constants, functions=function_names)
        module_body.append(ast.Assign(targets=[ast.Name(id=f"_c_{constant.name}", ctx=ast.Store())], value=value, type_comment=None))
        prior_constants.add(constant.name)

    tree = ast.fix_missing_locations(ast.Module(body=module_body, type_ignores=[]))
    try:
        code = compile(tree, "<aicl-python-backend>", "exec", dont_inherit=True, optimize=2)
    except (SyntaxError, TypeError, ValueError) as exc:
        raise AICLError("E-PYBACKEND-012", f"Could not compile generated Python AST: {exc}") from exc

    namespace: dict[str, Any] = {
        "__builtins__": {}, "min": min, "max": max,
        "_aicl_abs": abs, "_aicl_len": len, "_aicl_trim": _aicl_trim,
        "_aicl_not_empty": _aicl_not_empty, "_aicl_unique": _aicl_unique,
        "_aicl_map": _aicl_map, "_aicl_filter": _aicl_filter,
    }
    try:
        exec(code, namespace, namespace)
    except Exception as exc:
        raise AICLError("E-PYBACKEND-013", f"Could not initialise compiled AICL module: {type(exc).__name__}: {exc}") from exc

    return CompiledProgram(_namespace=namespace, _code=code, _functions={function.name: function for function in program.functions}, python_source=ast.unparse(tree))
