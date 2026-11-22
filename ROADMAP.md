# AICL roadmap

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

This roadmap adapts the project's report into small, verifiable increments. It is not a schedule commitment.

## Milestone 0 — research spike (current)

- [x] Define AICL-C 0.1 scalar/list subset.
- [x] Implement parser, type checker, typed canonical IR, deterministic module hash.
- [x] Implement bounded reference interpreter and hash-guarded transactional body patches.
- [x] Add examples, tests, CI, and optional tokenizer comparison.
- [ ] Build a 30–50 task benchmark corpus and collect equivalent Python/TypeScript baselines.
- [ ] Evaluate syntax variants across the actual target model tokenizers.

## Milestone 1 — language core

- [ ] Publish a formal grammar and operator/evaluation-order specification.
- [ ] Add records, options/results, and more complete static semantics.
- [ ] Add parser round-trip and malformed-input conformance suites.
- [ ] Decide stable symbol, module, and dependency identity rules.

## Milestone 2 — canonical IR

- [ ] Specify a versioned IR schema independently of Python implementation details.
- [ ] Define graph identity semantics beyond path-derived prototype IDs.
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

No token-efficiency claim or public beta until a reproducible benchmark demonstrates lower total workflow tokens with equivalent correctness and acceptable security results.
