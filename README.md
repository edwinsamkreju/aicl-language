# AICL — AI-First Compact Language

**A research-led prototype of a compact, typed programming representation designed for AI coding agents.**

Copyright © 2026 Edwin Sam K Reju. All rights reserved. See [COPYRIGHT.md](COPYRIGHT.md).

AICL separates the model-facing compact syntax (**AICL-C**) from the compiler-facing canonical typed representation (**AICL-IR**). This repository contains the AICL 0.1 research prototype: a parser, static type checker, typed JSON IR, deterministic module hashing, hash-guarded source patching, bounded reference interpreter, CLI, examples, tests, and a tokenizer-count harness.

> **Status:** early research prototype (0.1.0). Not a production compiler or secure general-purpose runtime. The report's proposed token-efficiency targets have not been demonstrated.

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

Expected output:

```json
{"result": 10}
```

Inspect canonical typed IR:

```bash
aicl ir examples/clamp.aicl
```

## AICL-C 0.1 examples

```aicl
aicl 0.1
f clamp(x:i64,lo:i64,hi:i64)->i64 !pure = max(lo,min(hi,x))
```

Pipeline calls inject the left-hand value as the first argument:

```aicl
aicl 0.1
f clean(xs:List[Str])->List[Str] !pure = xs |> map(trim) |> filter(not_empty) |> unique
```

Run:

```bash
aicl run examples/text_pipeline.aicl --function clean --args '[[" A ", "", "B", "A", " B "]]'
```

Expected output: `{"result": ["A", "B"]}`.

## Implemented subset

- Version declaration: `aicl 0.1`.
- Constants: `c name:Type = expression`.
- Typed pure functions: `f name(x:Type)->Type !pure = expression`.
- Types: `i64`, `f64`, `bool`, `Str`, and `List[T]`.
- Literals, local names, parentheses, unary operators, arithmetic, comparisons, boolean operators, calls, and `|>` pipelines.
- Built-ins: `min`, `max`, `trim`, `not_empty`, `unique`, `map`, `filter`, `abs`, and `len`.
- Deterministic typed JSON IR and SHA-256 module hash.
- Stable prototype IDs based on declaration and expression paths.
- Atomic source patching with a base-hash check and full candidate type validation.
- Bounded reference interpreter with execution-step, call-depth, and collection-size limits.

## Patch protocol

Get the current module hash from `aicl ir examples/patchable.aicl`, then create a JSON patch:

```json
{
  "base_hash": "sha256:REPLACE_WITH_CURRENT_HASH",
  "operations": [
    {"op": "replace_body", "function": "scale", "expression": "x * 3"}
  ]
}
```

Apply it with `aicl patch examples/patchable.aicl patch.json`. Only `replace_body` is supported. The patch is applied only if the base hash matches and the candidate module parses and type-checks. Failed validation leaves the source file unchanged.

## Token-count experiment

Install the optional benchmark dependency and run:

```bash
python -m pip install -e '.[bench]'
python benchmarks/compare_tokens.py --encoding cl100k_base
```

This reports source token counts for paired examples using the selected `tiktoken` encoding. It does **not** measure task success, total agent workflow tokens, retries, runtime, or security. Do not generalise results beyond the encoding and tasks reported. A larger benchmark with equivalent tasks, hidden tests, repeated trials, and full repair-loop accounting is still required.

## Repository structure

```text
src/aicl/                 Parser, type checker, typed IR, interpreter, patcher, CLI
spec/                     AICL-C grammar and draft AICL-IR JSON schema
examples/                 Runnable AICL-C programs
tests/                    Parser, type, interpreter, IR, and patch tests
benchmarks/               Python baseline and optional tokenizer harness
docs/decisions/            Architecture decision records
docs/INITIAL_BACKLOG.md    Engineering backlog
docs/REPORT_MAPPING.md     Proposal-to-implementation status
docs/TEST_REPORT.md        Initial test record
.github/workflows/         GitHub Actions CI
CONTRIBUTING.md            Contribution guidelines
SECURITY.md                Prototype security limitations
COPYRIGHT.md               Copyright and licence status
```

## Roadmap and limitations

See [ROADMAP.md](ROADMAP.md) and [docs/INITIAL_BACKLOG.md](docs/INITIAL_BACKLOG.md). The current prototype does not implement imports, records, generics, tensor shapes, async/streams, non-pure effects, capability grants, host calls, a binary IR encoding, native-token vocabulary, compiler lowering, MLIR/StableHLO/LLVM/Wasm backends, or a hardened sandbox. These remain future research and engineering tasks.

The report's central recommendation is preserved: validate token efficiency and correctness on a narrow prototype before investing in the full compiler/runtime. No token-savings claim is made.

## Copyright and licence

**Copyright © 2026 Edwin Sam K Reju. All rights reserved.**

No open-source licence has been selected. The copyright notice does not itself grant permission to copy, modify, distribute, sublicense, or sell this software. See [COPYRIGHT.md](COPYRIGHT.md) before reusing the project.

## Project report

The original AICL project report was intentionally **not included** in this repository upload, as requested. This README and the source documentation describe the implementation and its current boundaries.
