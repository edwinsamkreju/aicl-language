# AICL — AI-First Compact Language

**A research-led prototype of a compact, typed programming representation designed for AI coding agents.**

Copyright © 2026 Edwin Sam K Reju. All rights reserved. See [COPYRIGHT.md](COPYRIGHT.md).

AICL separates model-facing compact syntax (**AICL-C**) from compiler-facing canonical typed representation (**AICL-IR**). The repository contains an AICL 0.1 language prototype plus an experimental **AICL Patch Text 0.2** profile for smaller AI-generated edits.

> **Status:** early research prototype. Not a production compiler or secure general-purpose runtime. Token-efficiency claims for full programming tasks have not been demonstrated.

## Quick start

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
python -m pip install pytest
pytest
```

Check and run an example:

```bash
aicl check examples/clamp.aicl
aicl run examples/clamp.aicl --function clamp --args '[15, 0, 10]'
```

Expected output: `{"result": 10}`.

## AICL-C 0.1

```aicl
aicl 0.1
f clamp(x:i64,lo:i64,hi:i64)->i64 !pure = max(lo,min(hi,x))
```

Pipeline calls inject the left-hand value as the first argument:

```aicl
aicl 0.1
f clean(xs:List[Str])->List[Str] !pure = xs |> map(trim) |> filter(not_empty) |> unique
```

The current language subset includes scalar and list types, pure functions, expressions, pipelines, a static type checker, typed JSON IR, deterministic module hashing and a bounded reference interpreter. See [the grammar](spec/aicl-c-0.1.ebnf).

## New: node-level edits with AICL Patch Text 0.2

The first useful AI-efficiency improvement is not another keyword abbreviation. It is reducing the amount of code an agent must resend for a small edit.

Instead of replacing an entire function body, a model can address an expression by its IR node ID:

```text
aicl-patch 0.2
base sha256:<full canonical module hash>
node scale n:scale:body/right = 3
```

For the example function `scale(x) = x * 2`, this replaces only the right-hand literal node. The patch engine checks the full base hash, verifies that the addressed node belongs to the named function, rejects overlapping edits, applies all edits transactionally, and type-checks the complete candidate before writing it.

Compact patch files (`.aiclp`) and the existing JSON patch format are accepted by:

```bash
aicl patch examples/patchable.aicl examples/patch_scale_node.aiclp
```

The sample file is tied to the exact base hash of `examples/patchable.aicl`; regenerate its hash after changing that source. Node IDs are paths within that immutable base module, not permanent identities across arbitrary rewrites.

See [the patch grammar](spec/aicl-patch-0.2.ebnf) and [the working example](examples/patch_scale_node.aiclp).

## What the small-patch experiment shows

For one illustrative node edit, the compact patch text is **126 characters** versus **192 characters** for an equivalent minified JSON patch: a **34.38% character reduction** in this specific fixture.

Run the reproducible microbenchmark:

```bash
python benchmarks/compare_patch_payloads.py
```

For tokenizer measurements, install the optional benchmark dependency:

```bash
python -m pip install -e '.[bench]'
python benchmarks/compare_patch_payloads.py --encoding cl100k_base
```

The authoring environment did not have `tiktoken` installed, so no tokenizer result is claimed here. Character count is not token count. This microbenchmark also does not measure task success, context retrieval, retries, or full agent workflow cost.

## Other patch operation

Whole-body replacement remains available using JSON:

```json
{
  "base_hash": "sha256:REPLACE_WITH_CURRENT_HASH",
  "operations": [
    {"op": "replace_body", "function": "scale", "expression": "x * 3"}
  ]
}
```

## Repository structure

```text
src/aicl/                 Parser, type checker, typed IR, interpreter, patcher, CLI
spec/                     AICL-C grammar, IR schema, compact patch grammar
examples/                 AICL programs and compact patch example
tests/                    Language and node-patch conformance tests
benchmarks/               Token and patch-payload microbenchmarks
docs/                     Design decisions, report mapping, engineering backlog
.github/workflows/         GitHub Actions CI
```

## Limitations and next research

AICL-C 0.1 remains a small subset: imports, records, generics, tensor shapes, async/streams, non-pure effects, capability grants, host calls, binary IR encoding, native-token vocabulary, compiler lowering, MLIR/StableHLO/LLVM/Wasm backends, and a hardened sandbox are not implemented.

The next decisive experiment is an equivalent-task benchmark that counts all prompt and completion tokens across creation, context inspection, patching, testing, and repair. It must compare correctness and retry rates against Python and TypeScript on pinned tokenizers. The compact patch result is encouraging but not enough to claim that AICL as a whole is more token-efficient.

See [ROADMAP.md](ROADMAP.md) and [docs/INITIAL_BACKLOG.md](docs/INITIAL_BACKLOG.md).

## Copyright and licence

**Copyright © 2026 Edwin Sam K Reju. All rights reserved.**

No open-source licence has been selected. The copyright notice does not itself grant permission to copy, modify, distribute, sublicense, or sell this software. See [COPYRIGHT.md](COPYRIGHT.md).

The original project report PDF is intentionally not included in this repository.
