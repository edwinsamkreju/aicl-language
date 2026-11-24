# AICL roadmap

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

This roadmap adapts the project's report into small, verifiable increments. It is not a schedule commitment.

## Milestone 0 — research spike (current)

- [x] Define AICL-C 0.1 scalar/list subset.
- [x] Implement parser, type checker, typed canonical IR, deterministic module hash.
- [x] Implement bounded reference interpreter and hash-guarded whole-body patches.
- [x] Add stable-node patch operations and compact AICL Patch Text 0.2.
- [x] Add examples, tests, CI, and source-token / patch-payload microbenchmarks.
- [x] Define a deterministic 100-task paired Python/AICL corpus with 500 matched input cases.
- [x] Add correctness, source-size, tokenizer-payload and runtime-diagnostic harnesses; upload CI JSON reports.
- [x] Run and review hosted benchmark artifacts on Python 3.11 and 3.12; both report 500/500 matched cases.
- [x] Define a paired live-agent A/B protocol, request-level trace schema, deterministic 10-task/two-trial pilot, and trace analyzer.
- [ ] Execute the live-agent pilot with one pinned model snapshot and provider-reported request usage; review quality and budget before scaling.
- [ ] Measure compact node patches and complete agent workflows with actual target models and model-specific tokenizers.
- [ ] Expand beyond the prototype subset before making general-purpose language comparisons.

## Milestone 1 — language core

- [ ] Publish a complete grammar and operator/evaluation-order specification.
- [ ] Add records, options/results, and more complete static semantics.
- [ ] Add parser round-trip and malformed-input conformance suites.
- [ ] Decide stable symbol, module, and dependency identity rules.

## Milestone 2 — canonical IR

- [ ] Specify a versioned IR schema independently of Python implementation details.
- [ ] Evolve prototype path IDs into documented node-identity/version rules.
- [ ] Add canonical serialization compatibility tests and structured patch conflict diagnostics.

## Milestone 3 — compiler/runtime MVP

- [ ] Select one backend based on research-spike evidence.
- [ ] Implement lowering and interpreter/backend parity tests.
- [ ] Design capability enforcement and host ABI before enabling external effects.

## Milestone 4 — agent protocol

- [ ] Add compact context retrieval and structured diagnostics.
- [ ] Add agent create/inspect/patch/test/repair integration tests.
- [ ] Measure total prompt/completion tokens through success or retry limit.

## Release gate

No token-efficiency claim or public beta until reproducible equivalent-task benchmarks demonstrate lower total workflow tokens with equivalent correctness and acceptable security results.
