# Prototype test and measurement report

Recorded 24 November 2026. The earlier 22 November prototype measurements are retained in the project history.

## Existing prototype checks

- Local test and CLI checks are described in the original report entry from 22 November 2026.
- Compact patch representation microbenchmark: 126 characters for the AICL Patch Text fixture versus 192 characters for the minified JSON fixture, a 34.38% character reduction for that single example. This is not a tokenizer or full-workflow result.

## AICL-PY-100 equivalent-task benchmark

GitHub Actions run 49: [view run and artifacts](https://github.com/edwinsamkreju/aicl-language/actions/runs/45312741478).

- CI environments: Python 3.11.18 and 3.12.16.
- Existing automated pytest suite: 17 tests passed in each matrix job.
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

## Limits and next step

This suite tests only the currently implemented AICL-C 0.1 pure-function subset, using five fixed test cases per task. The 5.88% source-token reduction and 2.06% prompt-plus-source reduction are corpus-specific. No model was called, so actual completion tokens, tool traffic, patch/edit tokens, debug/retry tokens, completion rate, and end-to-end agent workflow cost remain unmeasured.

The next research step is a live-agent A/B test using the same model version, tokenizer, task prompts, tool budget, tests, repair policy, and randomized ordering, with complete per-task traces and multiple trials.
