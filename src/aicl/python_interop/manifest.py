"""Build compact, deterministic signatures for trusted Python modules."""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.metadata
import inspect
from functools import lru_cache
import json
import platform
import re
import sys
from collections.abc import Mapping
from types import ModuleType
from typing import Any, get_args, get_origin

from ..errors import AICLError
from ..syntax import parse_type

SCHEMA = "aicl-python-bindings/0.2"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TYPE_NAMES = {int: "i64", float: "f64", bool: "bool", str: "Str"}
_TYPE_TEXT = {"int": "i64", "float": "f64", "bool": "bool", "str": "Str"}
_PARAMETER_KINDS = {"positional_only", "positional_or_keyword", "keyword_only"}


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
        if isinstance(expression, ast.Subscript):
            container = expression.value
            is_list = (
                isinstance(container, ast.Name) and container.id in {"list", "List"}
            ) or (
                isinstance(container, ast.Attribute)
                and isinstance(container.value, ast.Name)
                and container.value.id == "typing"
                and container.attr == "List"
            )
            if is_list:
                return f"List[{_annotation_name(ast.unparse(expression.slice))}]"
        raise AICLError("E-PYBIND-004", f"Unsupported annotation {annotation!r}")
    if annotation in _TYPE_NAMES:
        return _TYPE_NAMES[annotation]
    if get_origin(annotation) is list:
        args = get_args(annotation)
        if len(args) == 1:
            return f"List[{_annotation_name(args[0])}]"
    raise AICLError("E-PYBIND-004", f"Unsupported annotation {annotation!r}")


def _aicl_type(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AICLError("E-PYBIND-014", f"{context} must be an AICL type string")
    try:
        return parse_type(value)
    except AICLError as exc:
        raise AICLError("E-PYBIND-014", f"Unsupported AICL type {value!r} in {context}") from exc


def _normalize_declaration(symbol: str, declaration: Any) -> dict[str, Any]:
    if not isinstance(declaration, Mapping) or set(declaration) != {"parameters", "return_type"}:
        raise AICLError("E-PYBIND-015", f"Explicit signature for {symbol!r} must contain parameters and return_type")
    raw_parameters = declaration["parameters"]
    if not isinstance(raw_parameters, list):
        raise AICLError("E-PYBIND-015", f"Parameters for {symbol!r} must be a list")

    parameters = []
    names = set()
    stage = 0
    optional_positional_seen = False
    for index, parameter in enumerate(raw_parameters):
        if not isinstance(parameter, Mapping) or set(parameter) != {"name", "type", "kind", "required"}:
            raise AICLError("E-PYBIND-015", f"Parameter {index} of {symbol!r} has an invalid shape")
        name = parameter["name"]
        if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
            raise AICLError("E-PYBIND-015", f"Parameter {index} of {symbol!r} has an invalid name")
        if name in names:
            raise AICLError("E-PYBIND-015", f"Duplicate parameter {name!r} in {symbol!r}")
        names.add(name)
        kind = parameter["kind"]
        if not isinstance(kind, str) or kind not in _PARAMETER_KINDS:
            raise AICLError("E-PYBIND-015", f"Parameter {name!r} has an unsupported calling convention")
        if not isinstance(parameter["required"], bool):
            raise AICLError("E-PYBIND-015", f"Parameter {name!r} required must be boolean")
        next_stage = {"positional_only": 0, "positional_or_keyword": 1, "keyword_only": 2}[kind]
        if next_stage < stage:
            raise AICLError("E-PYBIND-015", f"Invalid parameter ordering in signature for {symbol!r}")
        stage = next_stage
        if kind != "keyword_only":
            if optional_positional_seen and parameter["required"]:
                raise AICLError("E-PYBIND-015", f"Required positional parameter follows an optional parameter in {symbol!r}")
            optional_positional_seen = optional_positional_seen or not parameter["required"]
        parameters.append({
            "name": name,
            "type": _aicl_type(parameter["type"], f"parameter {name!r}"),
            "kind": kind,
            "required": parameter["required"],
        })
    return {
        "parameters": parameters,
        "return_type": _aicl_type(declaration["return_type"], f"return type of {symbol!r}"),
    }


@lru_cache(maxsize=256)
def _provider_record(root: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    if root in sys.stdlib_module_names:
        return ("stdlib", ())
    packages = importlib.metadata.packages_distributions()
    names = sorted(set(packages.get(root, [])), key=str.casefold)
    distributions = []
    for name in names:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        distributions.append((name, version))
    if distributions:
        return ("distribution", tuple(distributions))
    return ("unknown", ())


def _provider(module_name: str) -> dict[str, Any]:
    kind, distributions = _provider_record(module_name.partition(".")[0])
    if kind == "distribution":
        return {
            "kind": kind,
            "distributions": [
                {"name": name, "version": version}
                for name, version in distributions
            ],
        }
    return {"kind": kind}


def _validate_symbols(symbols: Any) -> list[str]:
    if not isinstance(symbols, (list, tuple)) or not symbols:
        raise AICLError("E-PYBIND-010", "Select at least one Python export")
    if not all(isinstance(symbol, str) for symbol in symbols):
        raise AICLError("E-PYBIND-002", "Export names must be strings")
    if any(not _IDENTIFIER.fullmatch(symbol) or symbol.startswith("_") for symbol in symbols):
        raise AICLError("E-PYBIND-002", "Export names must be public identifiers")
    if len(set(symbols)) != len(symbols):
        raise AICLError("E-PYBIND-011", "Duplicate export requested")
    return sorted(symbols)


def _signature_verified(function: Any, declaration: dict[str, Any]) -> bool:
    try:
        signature = inspect.signature(function, follow_wrapped=False, eval_str=False)
    except (TypeError, ValueError):
        return False
    kinds = {
        inspect.Parameter.POSITIONAL_ONLY: "positional_only",
        inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
        inspect.Parameter.KEYWORD_ONLY: "keyword_only",
    }
    actual = []
    for parameter in signature.parameters.values():
        if parameter.kind not in kinds:
            return False
        actual.append({
            "name": parameter.name,
            "kind": kinds[parameter.kind],
            "required": parameter.default is inspect.Parameter.empty,
        })
    expected = [
        {"name": p["name"], "kind": p["kind"], "required": p["required"]}
        for p in declaration["parameters"]
    ]
    return actual == expected


def _export(
    module: ModuleType,
    symbol: str,
    declaration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    function = vars(module).get(symbol)
    if function is None:
        raise AICLError("E-PYBIND-005", f"Module {module.__name__!r} has no direct export {symbol!r}")
    if inspect.isclass(function) or inspect.iscoroutinefunction(function):
        raise AICLError("E-PYBIND-006", f"Export {symbol!r} must be a synchronous callable, not a class or async function")

    if declaration is not None:
        if not callable(function):
            raise AICLError("E-PYBIND-007", f"Explicit export {symbol!r} is not callable")
        normalized = _normalize_declaration(symbol, declaration)
        type_source = "explicit"
        signature_verified = _signature_verified(function, normalized)
        parameters = normalized["parameters"]
        return_type = normalized["return_type"]
    else:
        if not (inspect.isfunction(function) or inspect.isbuiltin(function)):
            raise AICLError("E-PYBIND-007", f"Export {symbol!r} needs an explicit signature declaration")
        try:
            signature = inspect.signature(function, follow_wrapped=False, eval_str=False)
        except (TypeError, ValueError) as exc:
            raise AICLError("E-PYBIND-008", f"Cannot inspect signature for {symbol!r}; provide an explicit declaration: {exc}") from exc
        kinds = {
            inspect.Parameter.POSITIONAL_ONLY: "positional_only",
            inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
            inspect.Parameter.KEYWORD_ONLY: "keyword_only",
        }
        parameters = []
        for parameter in signature.parameters.values():
            if parameter.kind not in kinds:
                raise AICLError("E-PYBIND-009", f"Variadic parameter in {symbol!r} requires an explicit non-variadic declaration")
            parameters.append({
                "name": parameter.name,
                "type": _annotation_name(parameter.annotation),
                "kind": kinds[parameter.kind],
                "required": parameter.default is inspect.Parameter.empty,
            })
        return_type = _annotation_name(signature.return_annotation)
        type_source = "annotations"
        signature_verified = True

    return {
        "name": symbol,
        "kind": "function",
        "effect": "host",
        "capability": f"python:{module.__name__}.{symbol}",
        "type_source": type_source,
        "signature_verified": signature_verified,
        "parameters": parameters,
        "return_type": return_type,
    }


def _normalize_declarations(
    symbols: list[str],
    declarations: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if declarations is None:
        return {}
    if not isinstance(declarations, Mapping):
        raise AICLError("E-PYBIND-016", "Explicit declarations must be a JSON object keyed by export name")
    if not all(isinstance(name, str) for name in declarations):
        raise AICLError("E-PYBIND-016", "Declaration keys must be export-name strings")
    unknown = set(declarations) - set(symbols)
    if unknown:
        raise AICLError("E-PYBIND-016", f"Declarations contain unselected exports: {sorted(unknown)!r}")
    return {name: _normalize_declaration(name, declaration) for name, declaration in declarations.items()}


def build_manifest(
    module: ModuleType,
    symbols: list[str] | tuple[str, ...],
    *,
    declarations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build selected signatures from annotations or explicit declarations."""
    if not isinstance(module, ModuleType):
        raise AICLError("E-PYBIND-001", "Expected an imported Python module")
    module_name = getattr(module, "__name__", "")
    if not isinstance(module_name, str) or not module_name:
        raise AICLError("E-PYBIND-001", "Python module must have a non-empty __name__")
    selected = _validate_symbols(symbols)
    normalized = _normalize_declarations(selected, declarations)
    payload = {
        "schema": SCHEMA,
        "module": module_name,
        "provider": _provider(module_name),
        "python": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        "exports": [_export(module, symbol, normalized.get(symbol)) for symbol in selected],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"binding_hash": f"sha256:{digest}", **payload}


def load_manifest(
    module_name: str,
    symbols: list[str],
    *,
    declarations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Import a trusted module and create a signature-only binding manifest."""
    if not isinstance(module_name, str) or not module_name or not all(
        _IDENTIFIER.fullmatch(part) for part in module_name.split(".")
    ):
        raise AICLError("E-PYBIND-012", f"Invalid Python module name {module_name!r}")
    selected = _validate_symbols(symbols)
    normalized = _normalize_declarations(selected, declarations)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise AICLError("E-PYBIND-013", f"Could not import Python module {module_name!r}: {type(exc).__name__}: {exc}") from exc
    return build_manifest(module, selected, declarations=normalized)
