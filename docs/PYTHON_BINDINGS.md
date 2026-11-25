# AICL Python binding manifests 0.1

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Purpose

Create a compact, deterministic signature index for explicitly selected Python module functions. The manifest transfers API metadata, not implementation source or package documentation.

## Command

```bash
aicl py-manifest my_package.math_ops add normalize
```

The default output is compact JSON for machine consumption. Add `--pretty` for review. Only the listed direct module-level functions are included.

The module must already be installed in the active Python environment. **Importing a Python module executes its package initialization code**, so run this command only in a trusted environment with trusted packages. Manifest generation does not invoke the selected functions.

## Supported annotations

Bindings 0.1 maps `int`, `float`, `bool`, `str`, and nested `list[T]` / `typing.List[T]` annotations to AICL's current scalar and list types. Every parameter and return type must be annotated. Variadic parameters, async functions, classes, arbitrary objects, unions, tensors, and unknown annotations are rejected rather than guessed.

The manifest records parameter calling convention, whether a default exists, a host-effect marker, a capability name, package provider metadata, and a canonical SHA-256 binding hash. It never serializes Python default objects or function bodies.

## Contract and limits

The versioned schema is `spec/aicl-python-bindings-0.1.schema.json`. The API is in `src/aicl/python_interop/manifest.py`.

A manifest is an API description, not permission to call it. The runtime does not yet execute Python bindings from AICL source. A future host-call implementation must validate the binding hash, enforce an explicit capability grant, convert and validate arguments/results, and run under process/resource isolation appropriate to the package. Native extensions and annotated functions are not inherently safe.

The selected-symbol interface is intentionally narrow: it prevents agents from receiving an entire module's exported API when only one or two signatures are needed. There is no change to the AICL agent protocol or canonical AICL-IR, so existing agent payload sizes do not grow.
