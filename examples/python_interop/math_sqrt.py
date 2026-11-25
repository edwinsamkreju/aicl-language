"""Demonstrate a capability-granted binding to CPython's math.sqrt."""

from __future__ import annotations

import json
from pathlib import Path

from aicl.python_interop import PythonBindingRuntime, load_manifest


DECLARATIONS = json.loads(
    Path(__file__).with_name("math_bindings.json").read_text(encoding="utf-8")
)

manifest = load_manifest("math", ["sqrt"], declarations=DECLARATIONS)
runtime = PythonBindingRuntime.bind(
    manifest,
    grants={"python:math.sqrt"},
)

print(
    json.dumps(
        {"result": runtime.call("sqrt", [81.0])},
        sort_keys=True,
        separators=(",", ":"),
    )
)
