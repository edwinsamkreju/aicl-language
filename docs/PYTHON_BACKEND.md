# AICL Python backend 0.1

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Purpose

Reuse CPython as an execution engine for checked AICL programs without making Python the source language, semantic authority, or canonical intermediate representation. The backend is optional and adds no runtime package dependency.

## Pipeline

1. Parse AICL-C into the existing AICL syntax tree.
2. Run the existing AICL static type checker.
3. Lower each supported expression directly to Python AST nodes.
4. Compile the generated AST with CPython.
5. Execute with an explicit globals dictionary and an empty `__builtins__` mapping.

No Python source parsing, string interpolation, import statement, attribute access, or user-provided Python code is used by the lowering path. AICL identifiers are mapped to generated internal names, so Python keywords and helper-name collisions do not leak into the generated module.

## Supported subset

All currently type-checked AICL-C 0.1 pure expressions: literals, names, unary and binary operators, direct calls, pipelines, module constants, and functions. The existing pure built-ins are bridged, including list-returning `map` and `filter`, and ordered `unique`. Collection helpers retain the prototype's 10,000-item bound.

Use:

```bash
aicl run-python examples/clamp.aicl --function clamp --args '[15, 0, 10]'
```

The default `aicl run` command continues to use the reference interpreter.

## Boundaries and non-goals

- The canonical AICL-IR schema, module hash, compact source, patch format, and Agent Protocol 0.1 are unchanged.
- Python AST, bytecode, and object layout are backend details; they are not serialized into AICL-IR.
- Only the currently supported pure subset is executable. Imports, host calls, async effects, and external capabilities remain unsupported.
- An empty `__builtins__` namespace is defense in depth, not a hardened sandbox. There is no process isolation, resource quota, or AICL-level capability enforcement in this backend.
- The reference interpreter remains the semantic oracle. Differential tests must pass before backend features are expanded.
- Performance must be reported in two parts: one-time parse/type-check/compile cost and warmed invocation throughput. Do not claim a speedup until representative workloads show one after compile-time amortization.
- Token efficiency is preserved architecturally: no AICL syntax, IR fields, agent request/response fields, or default context payloads are added by this backend.

## Extension rule

New backend features must lower from already-defined, validated AICL semantics. Do not add Python-specific syntax or types to canonical IR merely to simplify this backend. Any proposed host-call boundary requires a separate typed capability design and security review.
