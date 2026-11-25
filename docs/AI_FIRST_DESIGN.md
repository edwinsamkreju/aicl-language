# AI-first architecture direction

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

## Objective

AICL should optimize for AI-driven program construction and transformation. Human readability is useful for debugging, review, and education, but it is not the primary design objective.

The optimization target is **total successful agent workflow cost**, not source character count alone:

- context required to understand the relevant program;
- input and output tokens for edits;
- number of tool/model round trips;
- parse/type/test/repair retries;
- execution and compilation cost;
- correctness, reliability, and security.

A shorter source file that causes more ambiguity, failures, or repair calls is not an improvement.

## Architectural layers

1. **Canonical semantic layer — AICL-IR.** A versioned typed representation is the semantic source of truth. It must be deterministic, content-addressable, and independent of the Python prototype implementation.
2. **Agent interaction layer — AICL Agent Protocol.** Agents retrieve bounded context slices, inspect symbol/type information, submit preconditioned patches, and receive structured diagnostics.
3. **Compact serialization layer — AICL-C and Patch Text.** Text is a transport/debug representation. It must preserve the canonical semantics and support targeted edits.
4. **Execution layer.** The bounded reference interpreter remains the semantic oracle. An optional CPython AST backend now lowers the checked pure-function subset to generated Python AST and executes it with an explicit globals table. This reuses CPython while keeping Python details out of canonical IR and agent payloads.

## Python ecosystem interoperability

Python is a first-class ecosystem target. The strategic objective is to let AICL agents use the existing Python package ecosystem and developer infrastructure rather than rebuild it. CPython is the initial execution engine; package interop, typed host bindings, and toolchain integration are subsequent layers. The language core and canonical IR remain independent of Python so other backends and implementations remain possible.

The detailed staged contract is in [Python interoperability strategy](PYTHON_INTEROP_STRATEGY.md). The key boundary is explicit typed imports and capability-granted host calls: AICL code must not gain ambient access to arbitrary modules, files, network, or processes. Agents should receive compact package manifests and only the signatures/types they need, not entire Python source trees or library documentation by default. That is how ecosystem reuse can coexist with low context-token usage.

## Python execution backend

The optional backend is isolated under `src/aicl/backend/python/`. It type-checks before lowering, generates AST nodes rather than source strings, compiles with CPython, and executes with an empty `__builtins__` mapping plus an explicit set of AICL runtime helpers. It preserves list-returning `map`/`filter` semantics and ordered `unique` behavior for the supported subset. The reference interpreter remains the default and is used as the parity oracle.

This is not a hardened sandbox: it has no explicit step/depth budget, capability system, or process isolation. It must not be used to execute untrusted AICL until those controls exist. The backend does not alter AICL source syntax, canonical IR, hashes, patch encoding, or JSONL agent responses. Compilation overhead and warmed execution performance still require measurement before making performance claims.

## Python API discovery

A signature-only Python binding manifest can be generated for an explicitly selected set of annotated module functions. Its deterministic hash and compact JSON layout let agents retrieve a few exact signatures instead of source files or full package documentation. Manifest generation imports trusted modules and does not call their functions. The in-process `PythonBindingRuntime` revalidates manifests, requires exact per-function grants, and validates argument and result types. It is not a sandbox; AICL source-level host-call dispatch, process isolation, and quotas remain future work.

## Canonical IR contract and transport

The repository now publishes `spec/aicl-ir-0.1.schema.json` as a language-neutral contract for the canonical typed IR document. The CLI supports `aicl ir FILE --compact` for whitespace-minimized canonical JSON and `--hash-only` for content-addressed module identity. Both use the same canonical IR and hash semantics as the Python implementation.

This makes the interchange format explicit, but does not yet prove implementation independence: a second-language encoder/decoder and cross-implementation hash conformance suite remain outstanding. A binary encoding should be evaluated only after these canonical semantics are stable.

## Implemented first slice

AICL Agent Protocol 0.1 provides:
- JSONL request/response transport over stdin/stdout;
- module signature index without expression bodies;
- single-function typed IR retrieval;
- single-node subtree retrieval by current IR node ID;
- structured type-check success and diagnostic errors;
- compact patch submission using AICL Patch Text 0.2;
- hash-guarded, type-checked, atomic source replacement.

This reduces unnecessary context transfer for supported operations. It does not yet provide binary IR, persistent semantic IDs, incremental dependency analysis, cancellation, multi-file transactions, or a model runner.

## Design constraints

- **Bounded context by default:** never return every function body when a signature index or one selected function is sufficient.
- **Deterministic addressing:** all patches bind to a canonical base hash; node IDs are valid only within that base version until durable identity is implemented.
- **Explicit mutation:** inspection/check operations are read-only. Only patch requests can modify a source file.
- **Structured failure:** parsers, type checkers, and patchers should return stable error codes; agents should not infer failure from prose.
- **Exact semantics:** compact encodings may abbreviate transport, never change operator, type, evaluation, or effect semantics.
- **Capability safety:** no implicit filesystem, network, process, or external side effects in the language. New effects require explicit capabilities and runtime enforcement.
- **Measure actual workflows:** report completion quality and all model/tool traffic. Tokenizer counts of stored source are not a substitute for provider-reported usage.

## Next technical priorities

1. Stabilize the IR contract and replace path-only node IDs with semantic identities plus version-scoped fallback paths.
2. Add node-local diagnostics and repair suggestions with machine-readable expected/actual types.
3. Add module/symbol indexes and dependency-aware minimal context retrieval.
4. Add binary canonical IR transport and compact patch encoding only after tokenizer/profile measurements.
5. Add multi-file transactions, test-oracle integration, and a persistent agent transport.
6. Execute controlled live-agent A/B experiments against Python and other serious baselines.

## Non-goals

AICL should not optimize for human typing shortcuts at the expense of machine reliability. It should also not assume that a custom model tokenizer or unreadable binary representation is automatically better: each transport profile must demonstrate reduced total agent cost on real tasks.
