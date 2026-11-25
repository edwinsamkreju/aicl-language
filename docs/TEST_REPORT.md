# Prototype test and measurement report

Recorded 24 November 2026. The earlier 22 November prototype measurements are retained in the project history.

## Existing prototype checks

- Local test and CLI checks are described in the original report entry from 22 November 2026.
- Compact patch representation microbenchmark: 126 characters for the AICL Patch Text fixture versus 192 characters for the minified JSON fixture, a 34.38% character reduction for that single example. This is not a tokenizer or full-workflow result.

## AICL-PY-100 equivalent-task benchmark

GitHub Actions run 49: [view run and artifacts](https://github.com/edwinsamkreju/aicl-language/actions/runs/45312741478).

- CI environments: Python 3.11.18 and 3.12.16.
- Existing automated pytest suite at that commit: 17 tests passed in each matrix job.
- Paired benchmark: 100 tasks, 10 task families, 500 matched input cases per environment.
- Correctness: **500/500 matched in each environment; zero mismatches**.
- Tokenizer: tiktoken cl100k_base.
- Source characters: Python 5,667; AICL 4,387; AICL 22.59% fewer.
- Source tokens: Python 1,888; AICL 1,777; AICL 5.88% fewer.
- Shared task-description prompt: 3,496 tokens on both sides.
- Shared prompt plus source: Python 5,384; AICL 5,273; AICL 2.06% fewer.
- Each job uploaded its JSON report as an artifact: aicl-py100-results-3.11 and aicl-py100-results-3.12.

### Runtime diagnostic

Ten thousand function calls per language were timed after AICL parse/type-check setup.

| Environment | CPython μs/call | AICL reference interpreter μs/call |
|---|---:|---:|
| Python 3.11.18 | 0.111 | 1.295 |
| Python 3.12.16 | 0.147 | 2.673 |

The AICL interpreter is slower in this test. This compares a Python-hosted AST interpreter with direct CPython function calls; it is not a benchmark of a compiled AICL runtime.

## Live-agent experiment framework

GitHub Actions run 69: [CI passed on Python 3.11 and 3.12](https://github.com/edwinsamkreju/aicl-language/actions/runs/45314779768).

- Automated tests: **24 passed** on each Python version.
- Added a strict JSONL trace schema for provider-reported request usage.
- Added a paired trace analyzer with per-language totals, success rates, per-stage token breakdown, tool/retry counts, optional cost estimates, aggregate and per-task paired comparisons.
- The analyzer requires one Python and one AICL record per task/trial, matching model snapshot, tokenizer and shared experiment-configuration SHA-256; it rejects duplicate or inconsistent records.
- Defined a deterministic 10-task, two-trial pilot: 40 total task-language runs.

**No live model calls have been performed.** This session does not provide an executable model-inference connection that exposes all request-level usage receipts. The trace framework and protocol are ready, but completion tokens, actual retries, and end-to-end live-agent savings are still unmeasured.

## AI-first agent interface 0.1

GitHub Actions run 73: [view run](https://github.com/edwinsamkreju/aicl-language/actions/runs/45641205723).

- Python 3.11 and 3.12 CI jobs both passed.
- Automated test suite: **33 passed** on each Python version.
- Added a JSONL agent protocol with bounded module-signature, function-IR, and expression-node inspection.
- Added structured check responses and machine-readable error codes.
- Added compact patch requests reusing AICL Patch Text 0.2; candidate source is hash-guarded, type-checked, and atomically replaced.
- Added protocol schema and design/roadmap documentation.

The new interface reduces unnecessary context retrieval for supported edit tasks. It has not yet been benchmarked against a live model for total tokens, task success, or end-to-end latency. No live model calls were made.

## Canonical IR contract and compact transport

Added `spec/aicl-ir-0.1.schema.json`, `aicl ir --compact`, and `aicl ir --hash-only`. The compact output is parsed in tests and compared semantically with pretty output; the hash-only mode is checked against the canonical module hash. This is a transport/contract improvement, not a binary IR or a live-agent token benchmark.

## Limits and next step

The 100-task suite tests only the currently implemented AICL-C 0.1 pure-function subset, using five fixed test cases per task. The 5.88% source-token reduction and 2.06% prompt-plus-source reduction are corpus-specific. No model was called in that benchmark, so actual completion tokens, tool traffic, patch/edit tokens, debug/retry tokens, completion rate, and end-to-end agent workflow cost remain unmeasured.

The next step is to run the 10-task/two-trial live-agent pilot using the same exact model snapshot, tokenizer, shared experiment configuration, task descriptions, test oracle, tools and repair limits for both languages. Preserve provider-reported usage events for every request and analyze them with benchmarks/analyze_agent_traces.py before scaling up.

