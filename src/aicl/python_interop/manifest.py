"""Build compact, deterministic signatures for trusted Python modules."""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import re
import sys
from types import ModuleType
from typing import Any, get_args, get_origin

from ..errors import AICLError

SCHEMA = "aicl-python-bindings/0.1"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TYPE_NAMES = {int: "i64", float: "f64", bool: "bool", str: "Str"}
_TYPE_TEXT = {"int": "i64", "float": "f64", "bool": "bool", "str": "Str"}


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Signature.empty:
        raise AICLError("E-PYBIND-003", "Every exported parameter and return value needs a supported type annotation")

    if isinstance(annotation, str):
        try:
            expression = ast.parse(annotation, mode="eval").body
        except SyntaxError as exc:
            raise AICLError("E-PYBIND-004", f"Unsupported annotation {annotation!r}") from exc
        if isinstance(expression, ast.Name) and expression.id in _TYPE_TEXT:
            return _TYPE_TEXT[expression.id]
        if (
            isinstance(expression, ast.Subscript)
            and isinstance(expression.value, ast.Name)
            and expression.value.id in {"list", "List"}
        ):
            return f"List[{_annotation_name(ast.unparse(expression.slice))}]"
        raise AICLError("E-PYBIND-004", f"Unsupported annotation {annotation!r}")

    if annotation in _TYPE_NAMES:
        return _TYPE_NAMES[annotation]

    if get_origin(annotation) is list:
        args = get_args(annotation)
        if len(args) == 1:
            return f"List[{_annotation_name(args[0])}]"

    raise AICLError("E-PYBIND-004", f"Unsupported annotation {annotation!r}")


def _provider(module_name: str) -> dict[str, Any]:
    root = module_name.partition(".")[0]
    if root in sys.stdlib_module_names:
        return {"kind": "stdlib"}

    packages = importlib.metadata.packages_distributions()
    names = sorted(set(packages.get(root, [])), key=str.casefold)
    distributions = []
    for name in names:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        distributions.append({"name": name, "version": version})
    if distributions:
        return {"kind": "distribution", "distributions": distributions}
    return {"kind": "unknown"}


def _export(module: ModuleType, symbol: str) -> dict[str, Any]:
    if not isinstance(symbol, str) or not _IDENTIFIER.fullmatch(symbol) or symbol.startswith("_"):
        raise AICLError("E-PYBIND-002", f"Export name must be a public identifier: {symbol!r}")

    function = vars(module).get(symbol)
    if function is None:
        raise AICLError("E-PYBIND-005", f"Module {module.__name__!r} has no direct export {symbol!r}")
    if inspect.iscoroutinefunction(function):
        raise AICLError("E-PYBIND-006", f"Async export {symbol!r} is not supported by bindings 0.1")
    if not (inspect.isfunction(function) or inspect.isbuiltin(function)):
        raise AICLError("E-PYBIND-007", f"Export {symbol!r} must be a module-level Python function")

    try:
        signature = inspect.signature(function, follow_wrapped=False, eval_str=False)
    except (TypeError, ValueError) as exc:
        raise AICLError("E-PYBIND-008", f"Cannot inspect signature for {symbol!r}: {exc}") from exc

    parameters = []
    kinds = {
        inspect.Parameter.POSITIONAL_ONLY: "positional_only",
        inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
        inspect.Parameter.KEYWORD_ONLY: "keyword_only",
    }
    for parameter in signature.parameters.values():
        if parameter.kind not in kinds:
            raise AICLError("E-PYBIND-009", f"Variadic parameter in {symbol!r} is not supported")
        parameters.append({
            "name": parameter.name,
            "type": _annotation_name(parameter.annotation),
            "kind": kinds[parameter.kind],
            "required": parameter.default is inspect.Parameter.empty,
        })

    return {
        "name": symbol,
        "kind": "function",
        "effect": "host",
        "capability": f"python:{module.__name__}.{symbol}",
        "parameters": parameters,
        "return_type": _annotation_name(signature.return_annotation),
    }


def build_manifest(module: ModuleType, symbols: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Describe only explicitly requested, annotated module-level functions."""
    if not isinstance(module, ModuleType):
        raise AICLError("E-PYBIND-001", "Expected an imported Python module")
    module_name = getattr(module, "__name__", "")
    if not isinstance(module_name, str) or not module_name:
        raise AICLError("E-PYBIND-001", "Python module must have a non-empty __name__")
    if not symbols:
        raise AICLError("E-PYBIND-010", "Select at least one Python export")
    if not all(isinstance(symbol, str) for symbol in symbols):
        raise AICLError("E-PYBIND-002", "Export names must be strings")
    if len(set(symbols)) != len(symbols):
        raise AICLError("E-PYBIND-011", "Duplicate export requested")

    payload = {
        "schema": SCHEMA,
        "module": module_name,
        "provider": _provider(module_name),
        "exports": [_export(module, symbol) for symbol in sorted(symbols)],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"binding_hash": f"sha256:{digest}", **payload}


def load_manifest(module_name: str, symbols: list[str]) -> dict[str, Any]:
    """Import a trusted module and create a signature-only binding manifest."""
    if not isinstance(module_name, str) or not module_name or not all(
        _IDENTIFIER.fullmatch(part) for part in module_name.split(".")
    ):
        raise AICLError("E-PYBIND-012", f"Invalid Python module name {module_name!r}")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise AICLError("E-PYBIND-013", f"Could not import Python module {module_name!r}: {type(exc).__name__}: {exc}") from exc
    return build_manifest(module, symbols)
