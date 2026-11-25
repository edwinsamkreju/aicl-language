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
4. **Execution layer.** A compiler/runtime executes verified IR under explicit resource and capability limits. The current Python AST interpreter is only a reference implementation.

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
