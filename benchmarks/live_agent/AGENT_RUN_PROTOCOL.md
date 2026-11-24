# Agent-run checklist for AICL-PY-100

Use this checklist unchanged for both language conditions. Store one trace record per task/language/trial.

## Before a paired trial

- [ ] Pin the exact model snapshot and tokenizer identifier.
- [ ] Pin sampling parameters, context limit, tool definitions and permissions; hash this shared configuration as SHA-256.
- [ ] Use the same task description, expected signature, logical tests, workspace scaffold and stop limits.
- [ ] Select a task/trial pair and randomized language order; log pair_order 1 for the first run and 2 for the second.
- [ ] Start from clean, independent workspaces so one language run cannot leak its solution to the other.

## During each run

- [ ] Tag every model request as create, inspect, patch, test, repair, or other.
- [ ] Record provider-reported input and output token usage for every request, including retries and repair turns.
- [ ] Record tool calls and request latency when available.
- [ ] Run the fixed tests without allowing the agent to modify the oracle.
- [ ] Stop at the predeclared wall-clock and repair/retry limits.
- [ ] Mark success only when every evaluation test passes.

## After each run

- [ ] Write a JSONL row conforming to trace.schema.json, including the shared experiment_config_hash in sha256:<64 lowercase hex> form.
- [ ] Keep the original provider usage receipt privately for auditing.
- [ ] Do not put credentials, private prompt transcripts, or user data into Git.
- [ ] Ensure the Python and AICL record share task ID and trial ID and use the exact same model snapshot and tokenizer.

## Analyze

Run:

~~~
python benchmarks/analyze_agent_traces.py --input pilot-traces.jsonl --output pilot-report.json
~~~

The analyzer rejects non-paired or mixed-model data instead of silently comparing it. It uses provider-reported request-level tokens, not source tokenization.
