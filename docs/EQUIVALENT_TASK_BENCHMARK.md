# AICL-PY-100: Equivalent-task benchmark

**Status:** benchmark corpus and automated harness implemented. The latest run is published as a GitHub Actions artifact; do not quote a result until that run completes successfully.

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

## Measurements and interpretation

When tiktoken is installed, the report includes **cl100k_base** source tokens for both complete source corpora and the tokens for a shared, deterministic task-description prompt corpus. The language-specific program source includes AICL's required module header. The prompt-plus-source total is the shared prompt count plus source count; therefore it is a reproducible token-payload estimate, not a live model trace.

The report separately includes source character counts, which are available even if tiktoken is not installed. Do not call character reduction a token reduction.

Runtime numbers are diagnostic only. CPython runs compiled Python functions, whereas this AICL prototype runs through a Python-hosted AST interpreter. These figures cannot establish how a future native AICL compiler would perform, nor are they a fair comparison of mature runtime implementations.

## What this benchmark does not measure

No language model is called. The benchmark therefore does **not** measure actual model input/output billing, completion tokens, tool-call tokens, context-retrieval traffic, edit-patch tokens, debugging messages, retries, or full agent task success. Those require a separate experiment that runs the same model and tokenizer, the same prompts and tool budget, randomized task ordering, and multiple trials while recording complete traces. The present harness leaves those fields as null rather than inventing estimates.

Five test cases per task provide a repeatable conformance sample, not proof of correctness over every possible input. The fixed suite can also favour the limited features it covers. Broader workloads must be added before making claims about general programming productivity or superiority to Python.

## CI output

The GitHub Actions matrix runs the correctness benchmark on Python 3.11 and 3.12 and uploads each JSON report as an artifact named **aicl-py100-results-<python-version>**. This preserves the machine-readable run data without committing environment-specific timing numbers into source control.

---

Copyright © 2026 Edwin Sam K Reju. All rights reserved.
