# AICL — AI-First Compact Language

**A research-led prototype of a compact, typed programming representation designed for AI coding agents.**

Copyright © 2026 Edwin Sam K Reju. All rights reserved. See [COPYRIGHT.md](COPYRIGHT.md).

AICL separates model-facing compact syntax (**AICL-C**) from compiler-facing canonical typed representation (**AICL-IR**). The repository contains an AICL 0.1 language prototype plus an experimental **AICL Patch Text 0.2** profile for smaller AI-generated edits.

> **Status:** early research prototype. Not a production compiler or secure general-purpose runtime. Token-efficiency claims for complete AI programming workflows have not been demonstrated.

## Quick start

Requires Python 3.11 or later.

~~~
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
python -m pip install pytest
pytest
~~~

Check and run an example:

~~~
aicl check examples/clamp.aicl
aicl run examples/clamp.aicl --function clamp --args '[15, 0, 10]'
~~~

Expected output: **{"result": 10}**.

## AICL-C 0.1

~~~aicl
aicl 0.1
f clamp(x:i64,lo:i64,hi:i64)->i64 !pure = max(lo,min(hi,x))
~~~

Pipeline calls inject the left-hand value as the first argument:

~~~aicl
aicl 0.1
f clean(xs:List[Str])->List[Str] !pure = xs |> map(trim) |> filter(not_empty) |> unique
~~~

The current language subset includes scalar and list types, pure functions, expressions, pipelines, a static type checker, typed JSON IR, deterministic module hashing and a bounded reference interpreter. See [the grammar](spec/aicl-c-0.1.ebnf).

## Node-level edits with AICL Patch Text 0.2

The first useful AI-efficiency improvement is not another keyword abbreviation. It is reducing the amount of code an agent must resend for a small edit.

Instead of replacing an entire function body, a model can address an expression by its IR node ID:

~~~
aicl-patch 0.2
base sha256:<full canonical module hash>
node scale n:scale:body/right = 3
~~~

For the example function **scale(x) = x * 2**, this replaces only the right-hand literal node. The patch engine checks the full base hash, verifies that the addressed node belongs to the named function, rejects overlapping edits, applies all edits transactionally, and type-checks the complete candidate before writing it.

Compact patch files (.aiclp) and the existing JSON patch format are accepted by:

~~~
aicl patch examples/patchable.aicl examples/patch_scale_node.aiclp
~~~

The sample file is tied to the exact base hash of examples/patchable.aicl; regenerate its hash after changing that source. Node IDs are paths within that immutable base module, not permanent identities across arbitrary rewrites.

See [the patch grammar](spec/aicl-patch-0.2.ebnf) and [the working example](examples/patch_scale_node.aiclp).

## Patch-payload microbenchmark

For one illustrative node edit, the compact patch text is **126 characters** versus **192 characters** for an equivalent minified JSON patch: a **34.38% character reduction** in this specific fixture.

Run the reproducible microbenchmark:

~~~
python benchmarks/compare_patch_payloads.py
~~~

For tokenizer measurements, install the optional benchmark dependency:

~~~
python -m pip install -e '.[bench]'
python benchmarks/compare_patch_payloads.py --encoding cl100k_base
~~~

Character count is not token count. This single-patch microbenchmark does not measure task success, context retrieval, retries, or full agent workflow cost.

## Major milestone: 100 equivalent Python/AICL tasks

The next milestone is now implemented as a reproducible benchmark suite: **100 paired pure-function tasks and 500 identical test cases** across ten supported task families.

~~~
python -m pip install -e '.[test,bench]'
python benchmarks/generate_suite.py --output /tmp/paired_suite.json
pytest
python benchmarks/run_equivalent_tasks.py --suite /tmp/paired_suite.json --encoding cl100k_base --repeats 20 --json-out benchmark-results.json
~~~

The runner checks Python/AICL output type and value parity, records interpreter setup and local runtime diagnostics, and counts both source tokens and a shared task-description prompt corpus when tiktoken is installed. GitHub Actions runs it on Python 3.11 and 3.12 and uploads the JSON results as build artifacts.

**Measurement boundary:** these are tokenizer counts for fixed task prompts and checked-in source, not observed model-generated completions or complete AI-agent workflows. No model is called, so edit/debug/retry/tool traffic and end-to-end model token usage remain unmeasured. Runtime compares CPython functions with a Python-hosted AICL reference interpreter; it is not a native compiler comparison. See [the benchmark protocol](docs/EQUIVALENT_TASK_BENCHMARK.md) before interpreting results.

## Repository structure

~~~
src/aicl/                 Parser, type checker, typed IR, interpreter, patcher, CLI
spec/                     AICL-C grammar, IR schema, compact patch grammar
examples/                 AICL programs and compact patch example
benchmarks/               Token, patch, and equivalent-task benchmarks
tests/                    Language, patch, and benchmark-corpus tests
docs/                     Benchmark protocol, design decisions, engineering backlog
.github/workflows/         GitHub Actions CI
~~~

## Limitations and next research

AICL-C 0.1 remains a small subset: imports, records, generics, tensor shapes, async/streams, non-pure effects, capability grants, host calls, binary IR encoding, native-token vocabulary, compiler lowering, MLIR/StableHLO/LLVM/Wasm backends, and a hardened sandbox are not implemented.

The 100-task milestone measures a bounded language subset, not general-purpose programming. The next major research step is a controlled live-agent trial with the same model, model-specific tokenizer, prompts, tests, tool permissions and repair policy for both languages, with complete traces and multiple randomized trials. It should report total tokens, correctness, retries, completion rate and cost without conflating source compactness with workflow efficiency.

See [ROADMAP.md](ROADMAP.md), [the benchmark protocol](docs/EQUIVALENT_TASK_BENCHMARK.md) and [docs/INITIAL_BACKLOG.md](docs/INITIAL_BACKLOG.md).

## Copyright and licence

**Copyright © 2026 Edwin Sam K Reju. All rights reserved.**

No open-source licence has been selected. The copyright notice does not itself grant permission to copy, modify, distribute, sublicense, or sell this software. See [COPYRIGHT.md](COPYRIGHT.md).

The original project report PDF is intentionally not included in this repository.
