# AICL — AI-First Compact Language

**A research-led prototype of a compact, typed programming representation designed for AI coding agents.**

Copyright © 2026 Edwin Sam K Reju. All rights reserved. See [COPYRIGHT.md](COPYRIGHT.md) for the copyright and licence status.

AICL separates the model-facing compact syntax (**AICL-C**) from the compiler-facing canonical typed representation (**AICL-IR**). This repository implements the first narrow experiment: a runnable AICL-C 0.1 subset, a typed canonical JSON IR, stable node identifiers, hash-guarded patches, a bounded reference interpreter, tests, and an optional token-count harness.

> **Status:** early research prototype (0.1.0). This is not a production compiler or secure general-purpose runtime. The report's proposed token-efficiency targets have not yet been demonstrated.

## Why this repository starts small

The project report recommends validating one central hypothesis first: can an AI system complete equivalent programming tasks with fewer **total tokenizer-measured workflow tokens** in AICL than in Python or TypeScript, without reducing correctness? A shorter source file alone is not sufficient. Failed attempts, debugging, patches, and retries must count.

The current implementation is intentionally narrow and dependency-free. Its reference interpreter has no filesystem, network, process, credential, or device operations.

## Quick start

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
python -m pip install pytest
pytest
```

Validate and run an example:

```bash
aicl check examples/clamp.aicl
aicl run examples/clamp.aicl --function clamp --args '[15, 0, 10]'
```

Expected result:

```json
{"result": 10}
```

Inspect canonical typed IR:

```bash
aicl ir examples/clamp.aicl
```

## AICL-C 0.1 example

```aicl
aicl 0.1
f clamp(x:i64,lo:i64,hi:i64)->i64 !pure = max(lo,min(hi,x))
```

A small data transformation uses pipeline syntax. The value on the left of `|>` is injected as the first argument of the operation on the right:

```aicl
aicl 0.1
f clean(xs:List[Str])->List[Str] !pure = xs |> map(trim) |> filter(not_empty) |> unique
```

Run it with:

```bash
aicl run examples/text_pipeline.aicl --function clean --args '[[" A ", "", "B", "A", " B "]]'
```

Expected result:

```json
{"result": ["A", "B"]}
```

## Implemented subset

- Version declaration: `aicl 0.1`.
- Constants: `c name:Type = expression`.
- Typed pure functions: `f name(x:Type)->Type !pure = expression`.
- Types: `i64`, `f64`, `bool`, `Str`, and `List[T]`.
- Literals, local names, parentheses, unary operators, arithmetic, comparisons, boolean operators, calls, and `|>` pipelines.
- Built-ins: `min`, `max`, `trim`, `not_empty`, `unique`, `map`, `filter`, `abs`, and `len`.
- Deterministic typed JSON IR and SHA-256 module hash.
- Stable prototype IDs based on declaration and expression paths.
- Atomic source patching with a base-hash check and type validation.
- Bounded reference interpreter with step and call-depth budgets.

See [the design decision](docs/decisions/0001-mvp-boundary.md) for current scope and deferred work.

## Patch protocol example

First obtain the current module hash from `aicl ir examples/patchable.aicl`. Then create a patch file:

```json
{
  "base_hash": "sha256:REPLACE_WITH_CURRENT_HASH",
  "operations": [
    {"op": "replace_body", "function": "scale", "expression": "x * 3"}
  ]
}
```

Apply it with:

```bash
aicl patch examples/patchable.aicl patch.json
```

Only `replace_body` is supported in this prototype. The patch is applied only if the base hash matches and the complete candidate module parses and type-checks. Failed validation leaves the source file unchanged.

## Token-count experiment

Install the optional benchmark dependency:

```bash
python -m pip install -e '.[bench]'
python benchmarks/compare_tokens.py --encoding cl100k_base
```

The script reports source token counts for paired examples using the explicitly selected `tiktoken` encoding. This is only a source-size measurement. It does **not** measure task success, total agent workflow tokens, retries, runtime, or security. `cl100k_base` is not a substitute for the tokenizer of every tested model. Do not generalise results beyond the encoding and tasks reported.

The next benchmark increment is a 30–50 task corpus with pinned models/tokenizers, repeated trials, hidden tests, repair limits, and Python/TypeScript baselines.

## Repository map

```text
src/aicl/             Parser, type checker, typed IR, interpreter, patcher, CLI
spec/                 Formal grammar and IR schema
examples/             Small AICL-C programs
benchmarks/           Paired baseline tasks and tokenizer harness
tests/                Conformance and transactional patch tests
docs/decisions/       Architecture decision records
.github/workflows/    Continuous integration
```

## Important limitations

The current prototype does not implement imports, records, generics, tensor shapes, async/streams, non-pure effects, capability grants, host calls, a binary IR encoding, native-token vocabulary, compiler lowering, MLIR/StableHLO/LLVM/Wasm backends, or a hardened sandbox. These remain design or research tasks—not implemented features.

The repository name is a working project name. Trademark, package-name, and domain availability have not been assessed. A project licence has deliberately not been selected yet; decide it before public redistribution or accepting contributions under a chosen licence.

## Copyright and licence status

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

This copyright notice records project attribution. It does not itself grant permission to copy, modify, publish, distribute, sublicense, or sell the software. No open-source licence has been selected. See [COPYRIGHT.md](COPYRIGHT.md).

## Project reference

The implementation is based on the supplied **AICL — AI-First Compact Language, Project Report, Version 1.0 (22 November 2026)**. The report's central two-layer architecture and research-first recommendation are preserved. The PDF report is included under `docs/AICL_Project_Report.pdf`.
