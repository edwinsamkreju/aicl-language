# Initial engineering backlog

These items translate the report's first-month plan and the AICL 0.2 patch experiment into verifiable tasks.

## Research spike

- [ ] Define 30–50 benchmark tasks spanning pure functions, data pipelines, incremental maintenance, and repair.
- [ ] Add equivalent Python and TypeScript baselines with acceptance tests.
- [ ] Pin target models, tokenizers, decoding settings, prompt templates, and retry limits.
- [ ] Prototype alternate compact source grammars and compare tokenizer counts and parse reliability.
- [ ] Measure total agent workflow tokens, including context retrieval, patching, testing, retries, and failures.

## Language and IR

- [x] Prototype canonical IR node paths usable for node-addressed edits.
- [x] Add a compact, hash-guarded AICL Patch Text 0.2 profile.
- [x] Reject overlapping node edits and type-check the entire candidate transaction.
- [ ] Publish complete EBNF, precedence, evaluation order, overflow, error, and numeric semantics.
- [ ] Add source maps and durable declaration identity semantics.
- [ ] Specify canonical IR schema/version compatibility and a deterministic binary encoding.
- [ ] Add transactional add/remove/rename and structured patch-conflict operations.

## Compiler and runtime

- [ ] Select one primary backend based on the benchmark spike; do not implement several backends in parallel.
- [ ] Implement compiler lowering and backend/reference-interpreter parity tests.
- [ ] Design the host ABI, opaque capabilities, policy grants, audit records, and resource budgets before adding external effects.
- [ ] Add fuzzing for parser, IR decoder, and patch envelopes.

## AI agent workflow

- [ ] Add compact context retrieval and machine-readable diagnostics with stable node IDs.
- [ ] Build create → parse → verify → run → test → patch → rerun workflow tests.
- [ ] Compare compact patches against ordinary code diffs on a representative task corpus.
