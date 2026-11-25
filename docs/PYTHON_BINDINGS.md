# AICL Python binding manifests and runtime 0.1

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Signature discovery

Create a compact, deterministic signature index for explicitly selected Python module functions. The manifest transfers API metadata, not implementation source or package documentation.

```bash
aicl py-manifest my_package.math_ops add normalize
```

The default output is compact JSON for machine consumption. Add `--pretty` for review. Only the listed direct module-level functions are included.

The module must be installed in the active Python environment. **Importing a Python module executes its package initialization code**, so run this command only in a trusted environment with trusted packages. Manifest generation does not invoke the selected functions.

Bindings 0.1 maps `int`, `float`, `bool`, `str`, and nested `list[T]` / `typing.List[T]` annotations to AICL scalar and list types. Every parameter and return value must be annotated. Variadic parameters, async functions, classes, arbitrary objects, unions, tensors, and unknown annotations are rejected rather than guessed.

The manifest records parameter calling convention, whether a default exists, a host-effect marker, a capability name, package provider metadata, and a canonical SHA-256 binding hash. It never serializes Python default objects or function bodies.

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

The binding runtime re-imports the module, rebuilds the manifest, and rejects a stale or modified manifest. It validates positional/keyword arguments, required parameters, AICL-compatible types, and return values. Supported mutable lists are copied across the boundary by value and bounded to 10,000 items per list and 32 nested list levels. Calls not included in the manifest or not covered by an explicit capability grant are rejected.

**This runs package code in the current Python process. It is not a sandbox.** Use only trusted packages and functions. Native extensions, annotated functions, and explicit grants are not proof of safety; the bridge has no process isolation, timeout, or resource quotas. AICL source-level host-call syntax and enforceable sandboxing are not implemented yet.

## Contract

- Schema: `spec/aicl-python-bindings-0.1.schema.json`
- Discovery API: `src/aicl/python_interop/manifest.py`
- Invocation API: `src/aicl/python_interop/runtime.py`

The selected-symbol interface prevents agents from receiving an entire module's API when only one or two signatures are needed. Manifests are deterministic and content-addressed. No changes are made to AICL-IR or Agent Protocol 0.1, so existing agent payloads do not grow.
