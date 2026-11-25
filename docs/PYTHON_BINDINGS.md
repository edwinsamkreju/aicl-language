# AICL Python binding manifests and runtime 0.2

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Signature discovery

Create a compact, deterministic signature index for explicitly selected Python module functions:

```bash
aicl py-manifest my_package.math_ops add normalize
```

Use `--pretty` for human review. Only explicitly selected, direct module-level exports are included.

Importing a Python module executes its package initialization code. Run discovery only against trusted packages in a trusted environment. Discovery does not invoke the selected functions.

## Type sources

Bindings 0.2 supports two explicit type sources:

- **Annotations:** maps `int`, `float`, `bool`, `str`, and nested `list[T]` / `typing.List[T]` to AICL scalar/list types.
- **Reviewed declarations:** supports APIs without usable annotations, including some native-extension APIs. A declaration is an explicit JSON contract authored by the project maintainer; AICL never guesses types.

For example, `math.sqrt` is a native-backed standard-library function. Its explicit declaration is:

```json
{
  "sqrt": {
    "parameters": [
      {"name": "x", "type": "f64", "kind": "positional_only", "required": true}
    ],
    "return_type": "f64"
  }
}
```

Run:

```bash
aicl py-manifest math sqrt --declarations examples/python_interop/math_bindings.json
python examples/python_interop/math_sqrt.py
```

The Python example uses `PythonBindingRuntime` with the exact capability `python:math.sqrt` and prints `{"result":9.0}`.

The manifest records `type_source` and `signature_verified`. The latter reports whether Python's inspectable call signature agrees with the declaration's parameter names, calling conventions, and required/default status. If a native callable has no inspectable signature, or the declaration differs, it is false. A declaration is still a maintainer assertion and must be checked against package documentation and tests. Variadic calling conventions are not supported.

Supported types are AICL's current scalar types and nested lists. Unions, arbitrary Python objects, tensors, NumPy arrays, and implicit conversions are rejected until their canonical representation and ownership/lifetime rules are defined.

The content-addressed manifest includes selected signatures, package/distribution versions, and Python implementation/version. It never serializes module source, function bodies, or Python default objects.

## Explicit in-process invocation

Python applications can bind a manifest and call only explicitly granted exports:

```python
from aicl.python_interop import PythonBindingRuntime, load_manifest

manifest = load_manifest("my_package.math_ops", ["add"])
runtime = PythonBindingRuntime.bind(
    manifest,
    grants={"python:my_package.math_ops.add"},
)
result = runtime.call("add", [2, 3])
```

For explicit declarations, pass the same `declarations` mapping to `load_manifest` before binding. The runtime revalidates the manifest against the installed module, package metadata, and interpreter; requires exact per-export grants; validates positional/keyword arguments and return values; and copies supported lists by value. Limits are 10,000 items per list, 100,000 aggregate list items across arguments/results, and 32 nested list levels. Awaitable results are rejected.

**This runs package code in the current Python process. It is not a sandbox.** Use only trusted packages and functions. Native extensions, annotations, explicit grants, and matching signatures are not proof of safety. The bridge has no process isolation, timeout, or resource quotas. AICL source-level imports and host-call syntax are not implemented yet.

## Contract

- Schema: `spec/aicl-python-bindings-0.2.schema.json`
- Historical schema: `spec/aicl-python-bindings-0.1.schema.json`
- Discovery: `src/aicl/python_interop/manifest.py`
- Invocation: `src/aicl/python_interop/runtime.py`
- Example: `examples/python_interop/math_sqrt.py`

The selected-symbol design keeps agent context to only APIs actually used. No AICL-IR or Agent Protocol fields are added by this optional binding feature.
