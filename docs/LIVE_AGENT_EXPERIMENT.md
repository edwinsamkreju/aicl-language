# Live-agent A/B experiment: AICL versus Python

**Status:** experiment protocol and trace analyzer implemented. No live model calls have been run by this repository change.

## Objective

Measure whether AICL reduces the complete cost of solving a programming task with an AI agent, while preserving correctness. This is distinct from source-token counts. A valid experiment must count every model request used to create, inspect, patch, test, debug, and repair the solution.

## Current environment limitation

This repository work can prepare the task protocol and analyze provider usage receipts. The current connected tools do not provide an executable model-inference session that can run a controlled pair of agent workspaces and expose all request usage. Therefore no live model was called and no workflow-token savings are claimed. The trace analyzer is ready to consume real runs once a model runner exports records in the published schema.

## Experiment design

### 1. Pilot first

Begin with a **10-task pilot and two paired trials** (40 total task-language runs). Review trace quality, task difficulty, completion rates, and estimated spend before scaling to all 100 tasks. Do not begin the 100-task, five-trial expansion until a budget cap and maximum repair count are explicitly set.

Use the same exact model snapshot and tokenizer for both languages. Pin the system instructions, temperature/sampling settings, maximum context, tool definitions, permissions, filesystem layout, test oracle, wall-clock limit, and retry/repair limit. Randomize and balance language order within each task/trial; record pair_order as 1 or 2. Do not run one language with additional hidden context or privileged tools.

### 2. Equivalent task workspace

For each task, provide the same natural-language specification, parameter and return types, constraints, tests, and workspace scaffolding. Only the implementation language and its concise language reference may differ. The Python agent edits Python files and runs Python tests; the AICL agent edits AICL files and runs the AICL checker/interpreter and the same logical tests. Neither agent may alter the test oracle.

Use the existing 100 paired tasks as the initial controlled workload. The present corpus is deliberately restricted to pure functions in AICL-C 0.1; do not treat it as representative of general Python engineering.

### 3. Agent stages

Tag each model request with one stage:

- create: first implementation from the task specification;
- inspect: retrieving or understanding existing workspace/context;
- patch: applying a targeted code edit;
- test: interpreting test output or requesting a test run;
- repair: diagnosing and fixing a failed test or incorrect result;
- other: other model requests needed to finish the task.

Count every model request, including failed attempts and retries. Tool calls and test executions should be counted from the agent runtime trace. Use actual provider-reported input and output token usage per request. Do not estimate completion tokens from character counts or substitute tiktoken source counts for billed usage.

### 4. Stop conditions and success

Use an agreed maximum repair/retry count and wall-clock limit fixed before the first run. A run succeeds only when all hidden evaluation tests pass within those limits. A run that times out, refuses the task, produces invalid code, or exhausts retries is a failure; retain all token usage accrued before failure. Run both languages for every task/trial, even when the first language fails.

### 5. Data capture and privacy

Write one JSONL record per task/language/trial, using the trace schema at ../benchmarks/live_agent/trace.schema.json. Each record must include the model ID and immutable model snapshot, tokenizer identifier, order, success/test counts, retry count, elapsed time, and one event for every model request. Each request event includes stage, provider-reported input/output tokens, tool-call count, and request latency when available.

Store only the minimum metadata needed for analysis. Do not commit API keys, access tokens, personal data, private prompts, or full workspace contents to this repository. Keep raw provider receipts private; preserve a local audit trail connecting each usage figure to its source receipt. Redact sensitive content before retaining any trace transcript.

### 6. Analyze

Install the project and run:

~~~
python benchmarks/analyze_agent_traces.py --input pilot-traces.jsonl --output pilot-report.json
~~~

Optional cost estimates require both rates, supplied explicitly in USD per million input and output tokens:

~~~
python benchmarks/analyze_agent_traces.py --input pilot-traces.jsonl --input-rate-per-million INPUT_RATE --output-rate-per-million OUTPUT_RATE
~~~

The analyzer rejects mixed model snapshots/tokenizers, duplicate rows, incomplete pairs, inconsistent test success, and invalid token counts. It reports success rate, total and mean input/output tokens, request/tool/retry counts, latency, stage breakdown, paired token reduction, and optional cost. Failed runs remain included in usage totals.

## Release-quality reporting

Publish per-language success rate first, then total tokens across all runs and tokens per successful task. Also report retries, tool calls, elapsed time, and cost under documented price assumptions. Include medians and per-task paired results, not only an aggregate mean. Compare token savings only alongside completion quality; a low-token result caused by more failures is not an efficiency win.

AICL supports a token-efficiency claim only if the live experiment demonstrates a repeatable reduction in complete workflow usage with statistically credible results and equivalent success rates. Until then, the evidence is limited to the first AICL-PY-100 source-token benchmark.

---

Copyright © 2026 Edwin Sam K Reju. All rights reserved.
