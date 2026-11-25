# AICL roadmap

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

The design target is an AI-native programming system. The canonical typed IR and agent protocol are intended to become the primary machine interface; compact source remains a serialization/debugging layer until the evidence justifies a lower-level representation.

## Milestone 0 — research prototype

- [x] Define AICL-C 0.1 scalar/list subset.
- [x] Implement parser, type checker, typed canonical IR, deterministic module hash.
- [x] Implement bounded reference interpreter and hash-guarded whole-body patches.
- [x] Add stable-node patch operations and compact AICL Patch Text 0.2.
- [x] Add deterministic 100-task paired Python/AICL benchmark.
- [x] Add source-size, tokenizer-payload, correctness, and runtime-diagnostic harnesses.
- [x] Define paired live-agent A/B protocol, request-level trace schema, 10-task/two-trial pilot, and trace analyzer.
- [x] Add AICL Agent Protocol 0.1: JSONL requests, bounded module/function/node inspection, structured checks, and hash-guarded patch operations.
- [ ] Execute the live-agent pilot with one pinned model snapshot and provider-reported request usage.
- [ ] Measure total agent workflow tokens, success rate, retries, tool calls, latency, and cost.

## Milestone 1 — machine-first semantic interface

- [x] Publish the versioned, language-neutral AICL-IR 0.1 JSON Schema contract and compact/hash-only CLI transport.\n- [ ] Implement an independent second-language IR encoder/decoder and cross-implementation canonical-hash conformance tests.
- [ ] Add stable semantic identities that survive unrelated tree edits.
- [ ] Add compact binary IR encoding and incremental serialization.
- [ ] Add structured diagnostics with exact node IDs and machine-actionable repair hints.
- [ ] Add dependency, import, symbol-index, and incremental invalidation models.
- [ ] Define canonical type constraints for records, options/results, generics, and tensor shapes.

## Milestone 2 — agent-native edit and verification loop

- [ ] Add multi-edit transactions with semantic conflict detection and merge support.
- [ ] Add dependency-aware context retrieval and automatic minimal context packing.
- [ ] Add explicit edit preconditions, postconditions, and test-oracle binding.
- [ ] Add a persistent agent service/stdio transport with request correlation and cancellation.
- [ ] Add agent adapters and benchmark real create/inspect/patch/test/repair loops.

## Milestone 3 — execution and compilation

- [x] Validate AICL Python AST backend 0.1 parity tests and CLI execution on Python 3.11 and 3.12.

- [ ] Design capability grants and effect boundaries before enabling external effects.
- [x] Add an optional CPython AST backend for the current pure-function subset; keep the canonical IR Python-independent.
- [ ] Benchmark compiled execution against the reference interpreter, including compile-time amortization.
- [ ] Select additional compiler backends from benchmark evidence.
- [x] Implement lowering and backend/reference-interpreter parity tests for the supported pure-function subset.
- [ ] Add deterministic, resource-bounded execution and hardened isolation.

## Release gate

No general AI-efficiency claim or public beta until independent, reproducible equivalent-task trials show lower complete workflow cost at equivalent correctness, with security and robustness results published.
