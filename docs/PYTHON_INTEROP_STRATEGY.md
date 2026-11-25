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

**First slice implemented:** `aicl py-manifest MODULE SYMBOL...` emits a deterministic, compact manifest for explicitly selected module-level functions. Bindings 0.2 accepts annotations or reviewed explicit signatures for unannotated/native APIs. The versioned contract is `spec/aicl-python-bindings-0.2.schema.json`; 0.1 remains archived. It rejects unsupported AICL types, variadic calling conventions, classes, and dynamic guesses. It records package/distribution and Python interpreter identity, signature-verification status, a canonical hash, and a host capability name. Module imports execute package initialization, so manifest generation is restricted to trusted environments.

**Second slice implemented:** `PythonBindingRuntime` revalidates a manifest against the installed package, requires explicit per-export capability grants, validates positional and keyword arguments against supported AICL types, and checks return values. It is an in-process bridge for trusted Python applications, not a sandbox. AICL source-level imports/host calls, process isolation, and quotas remain unimplemented.

Remaining language/runtime work:
- AICL source-level imports and host-call declarations, backed by a versioned language/IR revision.
- Capability grants carried by checked program artifacts and enforced by a supervised host-call worker.
- Process isolation, timeouts, memory/CPU quotas, cancellation, and stable error/traceback mapping.
- Rich value conversion for options/results, records, typed arrays/tensors, buffer ownership, and lifetime rules.
- Reproducible Python environment and lockfile resolution, including native ABI/platform identity.
- Conformance tests against exact Python/package versions, plus mixed-language project examples.

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
2. Define AICL source-level Python imports and host-call effects in a versioned IR revision.
3. Add a supervised, isolated worker for granted host calls before exposing imports to untrusted AICL.
4. Extend scalar/list conversions to options/results, records, and typed arrays with explicit ownership.
5. Add Python environment/lockfile resolution and reproducible builds.
6. Add bidirectional Python↔AICL embedding and developer-tool adapters.
7. Test representative native-extension and pure-Python package integrations.
8. Compare mixed-language workflows against Python-only baselines with provider-reported usage.

## Success criteria

AICL-Python interoperability succeeds when an existing Python project can adopt AICL for AI-heavy modules without losing access to its dependencies, tests, packaging, deployment, or developer tools—and when measured agent workflows are at least as correct and materially more efficient after counting all integration overhead.
