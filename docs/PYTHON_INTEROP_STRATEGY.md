# AICL Python interoperability strategy

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Strategic decision

Python ecosystem compatibility is a core AICL product objective, not merely a temporary implementation shortcut. AICL should offer an AI-first, compact, typed programming interface while allowing projects to reuse the mature CPython runtime, Python packages, and Python developer ecosystem.

The goal is not to replace Python's ecosystem. The goal is to make that ecosystem efficiently accessible from an AI-oriented language.

## Three distinct layers

### 1. CPython execution backend — initial slice implemented

AICL's checked pure-function subset can be lowered to Python AST, compiled, and executed by CPython. This reuses the runtime while keeping AICL syntax, canonical typed IR, hashes, patch format, and agent protocol independent of Python.

Status: implemented as an optional prototype backend. Differential CI tests pass on Python 3.11 and 3.12. The reference interpreter remains the semantic oracle and default execution path.

### 2. Typed Python module interoperability — next major engineering milestone

AICL should eventually import selected Python modules through explicit, statically described bindings. An illustrative future syntax could look like:

```aicl
aicl 0.2
import py.math as math
import py.numpy as np

f norm(x:Tensor[f32, 128])->f32 !host(math.sqrt) = ...
```

This is illustrative only; it is not accepted AICL syntax or a current implementation.

**First slice implemented:** `aicl py-manifest MODULE SYMBOL...` emits a deterministic, compact manifest for explicitly selected, type-annotated module-level functions. The versioned contract is `spec/aicl-python-bindings-0.1.schema.json`; the implementation is `src/aicl/python_interop/manifest.py`. It rejects unsupported annotations, variadic/async exports, classes, and dynamic guesses. It records a canonical hash and host capability name, but does not execute the function. Module imports execute package initialization, so manifest generation is restricted to trusted environments.

**Second slice implemented:** `PythonBindingRuntime` revalidates a manifest against the installed package, requires explicit per-export capability grants, validates positional and keyword arguments against supported AICL types, and checks return values. It is an in-process bridge for trusted Python applications, not a sandbox. AICL source-level imports/host calls, process isolation, and quotas remain unimplemented.

The full runtime interoperability design must still define:
- A versioned module-binding manifest containing exported symbols, signatures, type mappings, package identity, and version constraints.
- A typed value-conversion boundary between AICL values and Python objects.
- Explicit host-call declarations and capability grants; no ambient arbitrary module access.
- Effect annotations for calls that can access files, networks, processes, clocks, or mutable external state.
- Error conversion, exception semantics, cancellation, and resource limits.
- Reproducible environment resolution and dependency locking.
- A policy for native extensions and packages with platform-specific behavior.
- Conformance tests against the exact supported Python/package versions.

Start with pure, deterministic library functions and narrow data types. Expand to stateful or effectful libraries only after the capability and isolation model is enforceable.

### 3. Python toolchain and community integration

AICL should coexist with standard Python project workflows:
- Use Python virtual environments and standard package installation workflows.
- Reuse existing package metadata and dependency lockfiles rather than inventing a parallel package universe.
- Integrate with Python test runners and existing CI systems.
- Support calling AICL from Python and calling approved AICL modules from Python.
- Provide editor, language-server, debugger, formatter, and build-system adapters over time.
- Publish migration guides and examples showing how AICL can complement Python inside existing projects.

These are staged goals, not claims of current support.

## AI-efficiency requirements

Interoperability must not turn every agent request into a dump of Python library source or documentation.

1. Package discovery returns compact package identity and version metadata.
2. Symbol discovery returns names and signatures only.
3. Detailed type/behavior documentation is retrieved only for symbols actually used.
4. Manifests are deterministic, content-addressable, and cacheable.
5. Agent context retrieval is selective and bounded.
6. Edits remain in AICL's compact patch protocol; package implementation code is not copied into prompts.
7. Benchmarks measure the full workflow, including package discovery, type retrieval, model tokens, calls, retries, runtime, and dependency setup.

AICL should not claim lower token use simply because its own source is shorter. The measurement must include the additional interop metadata and tool traffic.

## Non-negotiable boundaries

- Python AST and bytecode are backend artifacts, not canonical AICL IR.
- Python packages do not become implicit language built-ins.
- An imported module does not automatically grant filesystem, network, process, or other ambient privileges.
- Untrusted AICL must not execute in-process with unrestricted Python objects.
- Native extensions and arbitrary Python callables are not automatically safe because their signatures are typed.
- The reference interpreter remains the semantic oracle for the pure subset; interop calls require explicit test doubles and integration conformance tests.
- Python package versions and environment identity must be recorded for reproducibility.

## Delivery sequence

1. Stabilize the current CPython backend and its differential test coverage.
2. Define AICL source-level host-call semantics and a versioned IR representation that reuses the capability naming established by the in-process bridge.
3. Extend the initial scalar/list type map to structured values, arrays, and ownership-aware conversions.
4. Prototype pure-function bindings for a small, well-understood standard-library surface.
5. Add a controlled third-party package adapter and lockfile/environment metadata.
6. Add bidirectional Python↔AICL embedding APIs.
7. Add developer-tool adapters and test real mixed-language projects.
8. Compare equivalent mixed-language tasks with Python-only baselines using provider-reported agent usage and end-to-end correctness.

## Success criteria

AICL-Python interoperability succeeds when an existing Python project can adopt AICL for AI-heavy modules without losing access to its dependencies, tests, packaging, deployment, or developer tools—and when measured agent workflows are at least as correct and materially more efficient after counting all integration overhead.
