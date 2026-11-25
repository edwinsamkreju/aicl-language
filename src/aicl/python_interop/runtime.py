"""Explicit-capability invocation of selected Python binding manifests."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from ..errors import AICLError
from .manifest import SCHEMA, load_manifest


_MAX_LIST_ITEMS = 10_000
_MAX_TOTAL_LIST_ITEMS = 100_000
_MAX_VALUE_DEPTH = 32


def _convert(
    value: Any,
    type_name: str,
    *,
    path: str,
    depth: int = 0,
    item_budget: list[int] | None = None,
) -> Any:
    """Validate an AICL value and detach mutable lists from host-owned objects."""
    if item_budget is None:
        item_budget = [0]
    if depth > _MAX_VALUE_DEPTH:
        raise AICLError("E-PYBIND-038", f"{path} exceeds the {_MAX_VALUE_DEPTH}-level nesting limit")
    if type_name == "bool" and isinstance(value, bool):
        return value
    if type_name == "i64":
        if isinstance(value, int) and not isinstance(value, bool) and -(2**63) <= value < 2**63:
            return value
    elif type_name == "f64":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    elif type_name == "Str":
        if isinstance(value, str):
            return value
    elif type_name.startswith("List[") and type_name.endswith("]"):
        if isinstance(value, list):
            if len(value) > _MAX_LIST_ITEMS:
                raise AICLError("E-PYBIND-037", f"{path} exceeds the {_MAX_LIST_ITEMS}-item list limit")
            item_budget[0] += len(value)
            if item_budget[0] > _MAX_TOTAL_LIST_ITEMS:
                raise AICLError(
                    "E-PYBIND-039",
                    f"{path} exceeds the {_MAX_TOTAL_LIST_ITEMS}-item aggregate value limit",
                )
            item_type = type_name[5:-1]
            return [
                _convert(
                    item,
                    item_type,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                    item_budget=item_budget,
                )
                for index, item in enumerate(value)
            ]
    raise AICLError("E-PYBIND-034", f"{path} must match {type_name}")


class PythonBindingRuntime:
    """In-process bridge restricted to a pinned manifest and explicit grants.

    This is an interoperability boundary, not a sandbox. Imported packages execute
    in the current process and must be trusted by the embedding application.
    """

    def __init__(self, module: Any, exports: dict[str, dict[str, Any]], grants: frozenset[str]) -> None:
        self._module = module
        self._exports = exports
        self._grants = grants
        self._functions = {name: vars(module)[name] for name in exports}

    @classmethod
    def bind(cls, manifest: Mapping[str, Any], *, grants: Iterable[str]) -> "PythonBindingRuntime":
        if not isinstance(manifest, Mapping) or manifest.get("schema") != SCHEMA:
            raise AICLError("E-PYBIND-020", "Unsupported or malformed Python binding manifest")
        module_name = manifest.get("module")
        exports = manifest.get("exports")
        expected_hash = manifest.get("binding_hash")
        if not isinstance(module_name, str) or not isinstance(exports, list) or not exports:
            raise AICLError("E-PYBIND-020", "Malformed Python binding manifest")

        names = []
        declared: dict[str, dict[str, Any]] = {}
        capabilities = set()
        for entry in exports:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("name"), str)
                or not isinstance(entry.get("capability"), str)
            ):
                raise AICLError("E-PYBIND-020", "Malformed Python export declaration")
            name = entry["name"]
            if name in declared:
                raise AICLError("E-PYBIND-020", f"Duplicate binding export {name!r}")
            names.append(name)
            declared[name] = entry
            capabilities.add(entry["capability"])

        if isinstance(grants, str):
            raise AICLError("E-PYBIND-023", "Capabilities must be an iterable of capability strings")
        try:
            granted = frozenset(grants)
        except TypeError as exc:
            raise AICLError("E-PYBIND-023", "Capabilities must be an iterable of strings") from exc
        if not granted:
            raise AICLError("E-PYBIND-023", "At least one explicit capability grant is required")
        if not all(isinstance(capability, str) for capability in granted):
            raise AICLError("E-PYBIND-023", "Capabilities must be strings")
        unknown = granted - capabilities
        if unknown:
            raise AICLError("E-PYBIND-024", f"Grant does not exist in manifest: {sorted(unknown)!r}")

        explicit_declarations = {}
        for entry in exports:
            if entry.get("type_source") == "explicit":
                explicit_declarations[entry["name"]] = {
                    "parameters": entry.get("parameters"),
                    "return_type": entry.get("return_type"),
                }
            elif entry.get("type_source") != "annotations":
                raise AICLError("E-PYBIND-020", "Unknown Python binding type source")

        try:
            current = load_manifest(
                module_name,
                names,
                declarations=explicit_declarations or None,
            )
            module = importlib.import_module(module_name)
        except AICLError:
            raise
        except Exception as exc:
            raise AICLError("E-PYBIND-021", f"Could not load binding module: {type(exc).__name__}: {exc}") from exc

        if not isinstance(expected_hash, str) or current != dict(manifest):
            raise AICLError("E-PYBIND-022", "Binding manifest is stale or does not match the installed module")

        return cls(module, {entry["name"]: entry for entry in current["exports"]}, granted)

    def call(
        self,
        name: str,
        arguments: Sequence[Any] = (),
        keywords: Mapping[str, Any] | None = None,
    ) -> Any:
        entry = self._exports.get(name)
        if entry is None:
            raise AICLError("E-PYBIND-025", f"Python binding {name!r} is not in the pinned manifest")
        capability = entry["capability"]
        if capability not in self._grants:
            raise AICLError("E-PYBIND-026", f"Missing capability grant: {capability}")

        if not isinstance(arguments, (list, tuple)):
            raise AICLError("E-PYBIND-027", "Positional arguments must be a list or tuple")
        if keywords is None:
            keywords = {}
        if not isinstance(keywords, Mapping) or not all(isinstance(key, str) for key in keywords):
            raise AICLError("E-PYBIND-028", "Keyword arguments must be a mapping with string keys")

        parameters = entry["parameters"]
        positional = [p for p in parameters if p["kind"] in {"positional_only", "positional_or_keyword"}]
        if len(arguments) > len(positional):
            raise AICLError("E-PYBIND-029", f"Too many positional arguments for {name!r}")

        supplied: dict[str, Any] = {
            parameter["name"]: value for parameter, value in zip(positional, arguments)
        }
        parameter_by_name = {parameter["name"]: parameter for parameter in parameters}
        for key, value in keywords.items():
            parameter = parameter_by_name.get(key)
            if parameter is None:
                raise AICLError("E-PYBIND-030", f"Unknown keyword {key!r} for {name!r}")
            if parameter["kind"] == "positional_only":
                raise AICLError("E-PYBIND-031", f"Parameter {key!r} is positional-only")
            if key in supplied:
                raise AICLError("E-PYBIND-032", f"Multiple values for parameter {key!r}")
            supplied[key] = value

        item_budget = [0]
        for parameter in parameters:
            key = parameter["name"]
            if parameter["required"] and key not in supplied:
                raise AICLError("E-PYBIND-033", f"Missing required parameter {key!r}")
            if key in supplied:
                supplied[key] = _convert(
                    supplied[key],
                    parameter["type"],
                    path=f"Argument {key!r}",
                    item_budget=item_budget,
                )

        call_args = []
        for parameter in parameters:
            if parameter["kind"] != "positional_only":
                continue
            key = parameter["name"]
            if key not in supplied:
                break
            call_args.append(supplied[key])

        call_kwargs = {
            parameter["name"]: supplied[parameter["name"]]
            for parameter in parameters
            if parameter["kind"] != "positional_only" and parameter["name"] in supplied
        }
        try:
            result = self._functions[name](*call_args, **call_kwargs)
        except Exception as exc:
            raise AICLError("E-PYBIND-035", f"Python host call failed: {type(exc).__name__}: {exc}") from exc

        if inspect.isawaitable(result):
            close = getattr(result, "close", None)
            if callable(close):
                close()
            raise AICLError("E-PYBIND-040", "Awaitable host-call results are not supported by bindings 0.2")

        return _convert(
            result,
            entry["return_type"],
            path=f"Python result from {name!r}",
            item_budget=item_budget,
        )
