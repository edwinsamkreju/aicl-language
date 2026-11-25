# AICL roadmap

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

The design target is an AI-native programming system. Canonical typed IR and the agent protocol remain the primary machine interface. Python is the first execution ecosystem, not the semantic definition of AICL.

## Milestone 0 — research prototype

- [x] Define the AICL-C 0.1 scalar/list subset.
- [x] Implement parser, type checker, canonical typed IR, and deterministic module hash.
- [x] Implement bounded reference interpreter and hash-guarded patches.
- [x] Add stable-node patch operations and compact AICL Patch Text 0.2.
- [x] Add deterministic 100-task paired Python/AICL benchmark.
- [x] Add source-size, tokenizer-payload, correctness, and runtime-diagnostic harnesses.
- [x] Define paired live-agent A/B protocol, request-level trace schema, 10-task/two-trial pilot, and trace analyzer.
- [x] Add AICL Agent Protocol 0.1: JSONL, bounded module/function/node inspection, structured checks, and hash-guarded patching.
- [ ] Execute the live-agent pilot with one pinned model snapshot and provider-reported usage.
- [ ] Measure complete agent workflow tokens, success, retries, tool calls, latency, and cost.

## Milestone 1 — machine-first semantic interface

- [x] Publish versioned, language-neutral AICL-IR 0.1 JSON Schema and compact/hash-only transport.
- [ ] Implement independent second-language IR encoder/decoder and cross-implementation hash conformance tests.
- [ ] Add stable semantic identities that survive unrelated tree edits.
- [ ] Add compact binary IR encoding and incremental serialization.
- [ ] Add structured diagnostics with exact node IDs and machine-actionable repair hints.
- [ ] Add dependency, import, symbol-index, and incremental invalidation models.
- [ ] Define canonical type constraints for records, options/results, generics, and tensor shapes.

## Milestone 2 — agent-native edit and verification loop

- [ ] Add multi-edit transactions with semantic conflict detection and merge support.
- [ ] Add dependency-aware context retrieval and automatic minimal context packing.
- [ ] Add explicit edit preconditions, postconditions, and test-oracle binding.
- [ ] Add persistent agent transport with request correlation and cancellation.
- [ ] Add agent adapters and benchmark real create/inspect/patch/test/repair loops.

## Milestone 3 — Python ecosystem and execution

- [x] Add optional CPython AST backend 0.1 for the checked pure-function subset.
- [x] Verify backend/reference-interpreter parity and CLI execution on Python 3.11 and 3.12.
- [x] Add selected-symbol Python API manifests with strict annotation mapping, deterministic hashes, and package metadata.
- [x] Add an in-process Python binding runtime with manifest revalidation, explicit per-function grants, argument validation, and return validation.
- [ ] Define AICL source-level Python imports and host-call semantics in a versioned language/IR revision.
- [ ] Add enforceable process isolation, resource quotas, cancellation, and safe handling for untrusted host calls.
- [ ] Expand type conversion to options/results, records, tensor/array views, and explicit ownership/lifetime rules.
- [ ] Add Python environment/lockfile integration and reproducible package resolution.
- [ ] Add bidirectional Python↔AICL embedding APIs and developer-tool adapters.
- [ ] Benchmark mixed Python/AICL library workflows against Python-only baselines, including compile/setup cost and complete agent usage.

## Milestone 4 — additional execution targets

- [ ] Benchmark alternative backends before selecting a native target.
- [ ] Implement backend/reference-interpreter conformance for new targets.
- [ ] Add deterministic, resource-bounded execution and hardened isolation across supported targets.

## Release gate

No general AI-efficiency or production-security claim until independent, reproducible equivalent-task trials show lower complete workflow cost at equivalent correctness, and security/resource-isolation results are published.
