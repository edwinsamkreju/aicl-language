# Initial engineering backlog

These items translate the report's first-month plan into issues that can be tackled independently.

## Research spike

- [ ] Define 30–50 benchmark tasks spanning pure functions, data pipelines, incremental maintenance, and repair.
- [ ] Add equivalent Python and TypeScript baselines with acceptance tests.
- [ ] Pin target models, tokenizers, decoding settings, prompt templates, and retry limits.
- [ ] Prototype at least two alternate compact grammars and compare token counts and parse reliability.

## Language and IR

- [ ] Publish complete EBNF, precedence, evaluation order, overflow, error, and numeric semantics.
- [ ] Add source maps and stable declaration IDs.
- [ ] Specify canonical IR schema/version compatibility and a deterministic binary encoding.
- [ ] Add transactional `add_node`, `remove_declaration`, and `rename_symbol` patch operations.

## Compiler and runtime

- [ ] Select one primary backend based on the benchmark spike; do not implement several backends in parallel.
- [ ] Implement compiler lowering and backend/reference-interpreter parity tests.
- [ ] Design the host ABI, opaque capabilities, policy grants, audit records, and resource budgets before adding external effects.
- [ ] Add fuzzing for parser, IR decoder, and patch envelopes.

## AI agent workflow

- [ ] Add compact context retrieval and machine-readable diagnostics with stable node IDs.
- [ ] Build create → parse → verify → run → test → patch → rerun workflow tests.
- [ ] Measure full workflow tokens, including inspection, repair, tests, and failed attempts.
