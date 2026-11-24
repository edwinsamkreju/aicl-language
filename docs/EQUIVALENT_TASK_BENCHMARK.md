# AICL-PY-100: Equivalent-task benchmark

**Status:** first hosted benchmark completed successfully on Python 3.11 and 3.12. GitHub Actions run 49 uploaded JSON artifacts for both environments.

## Purpose

Compare AICL-C 0.1 with Python on the same small pure-function tasks. This is the controlled step beyond the earlier single-function and patch-payload examples. It checks semantic output parity on a bounded corpus and records source and tokenizer sizes separately.

## Frozen task suite

The deterministic corpus in **benchmarks/generate_suite.py** contains exactly 100 paired task definitions, generated from ten task families:

- integer addition, subtraction, multiplication, minimum, maximum, absolute difference, and greater-than comparison;
- string suffix appending and whitespace trimming;
- stable-order integer-list deduplication.

There are ten parameterized tasks in each family. Each task has the same five test inputs for Python and AICL, for **500 paired input cases**. The suite is intentionally limited to features that exist in the current AICL-C 0.1 prototype. It is not a general Python benchmark and does not test I/O, imports, classes, async code, libraries, or large application maintenance.

Export the frozen suite to JSON:

~~~
python benchmarks/generate_suite.py --output /tmp/paired_suite.json
~~~

## Run locally

~~~
python -m pip install -e '.[test,bench]'
pytest
python benchmarks/generate_suite.py --output /tmp/paired_suite.json
python benchmarks/run_equivalent_tasks.py --suite /tmp/paired_suite.json --encoding cl100k_base --repeats 20 --json-out benchmark-results.json
~~~

The runner checks that Python and the AICL reference interpreter return the same type and value on all 500 cases. It also records AICL parse/type-check setup time and repeated-call timings. If no JSON suite is supplied, the runner builds the deterministic corpus directly from the generator.

## First hosted result — 24 November 2026

GitHub Actions run 49 completed successfully for Python 3.11 and 3.12. Both matrix jobs passed the existing test suite, the 100-task benchmark and CLI smoke tests, and uploaded JSON result artifacts.

| Metric | Python | AICL | Difference |
|---|---:|---:|---:|
| Program source characters | 5,667 | 4,387 | AICL 22.59% fewer |
| Program source tokens | 1,888 | 1,777 | AICL 5.88% fewer |
| Shared task prompt tokens | 3,496 | 3,496 | Equal |
| Shared prompt + source tokens | 5,384 | 5,273 | AICL 2.06% fewer |

Both language implementations returned identical values and types on **500 / 500 cases**, with **zero mismatches**, on each Python matrix version.

The 111-token difference in program source is real for this generated corpus and selected encoding. It falls to a 2.06% difference when the same task descriptions are included. This is a limited serialization result; it should not be generalized to arbitrary code or interpreted as model-generated token savings.

### Runtime diagnostic

The benchmark made 10,000 calls per language after one AICL parse/type-check setup. These are recorded as reference-interpreter diagnostics only:

| CI environment | CPython per call | AICL reference interpreter per call |
|---|---:|---:|
| Python 3.11.18 | 0.111 μs | 1.295 μs |
| Python 3.12.16 | 0.147 μs | 2.673 μs |

The AICL reference interpreter is slower on this microbenchmark. It is implemented in Python and interprets AICL expression trees, while the Python baseline is direct CPython function calls. This does not predict the performance of a future native AICL compiler.

**Run record:** [GitHub Actions run 49](https://github.com/edwinsamkreju/aicl-language/actions/runs/45312741478). It contains the downloadable artifacts **aicl-py100-results-3.11** and **aicl-py100-results-3.12**.

## Measurements and interpretation

The token report uses tiktoken with **cl100k_base**. It counts the complete Python and AICL source corpora and a shared, deterministic task-description prompt corpus. The AICL source includes its required module header. The prompt-plus-source total is the shared prompt count plus source count; therefore it is a reproducible token-payload estimate, not a live model trace.

The report separately includes source character counts, which are available even if tiktoken is not installed. Do not call character reduction a token reduction.

## What this benchmark does not measure

No language model is called. The benchmark therefore does **not** measure actual model input/output billing, completion tokens, tool-call tokens, context-retrieval traffic, edit-patch tokens, debugging messages, retries, or full agent task success. Those require a separate experiment that runs the same model and tokenizer, the same prompts and tool budget, randomized task ordering, and multiple trials while recording complete traces. The present harness leaves those fields as null rather than inventing estimates.

Five test cases per task provide a repeatable conformance sample, not proof of correctness over every possible input. The fixed suite can also favour the limited features it covers. Broader workloads must be added before making claims about general programming productivity or superiority to Python.

## Next experiment

Run a live-agent A/B benchmark using the same model version, model-specific tokenizer, task descriptions, system instructions, available context, tool permissions, test suite, repair limits, and randomized task order. Capture the full request/response/tool trace for each run. Report completion rate, correctness, total input and output tokens, patch/edit/debug/retry tokens, number of tool calls, elapsed time, and cost. Run multiple trials and publish raw per-task data. Only that experiment can support claims about end-to-end AI workflow efficiency.

---

Copyright © 2026 Edwin Sam K Reju. All rights reserved.
