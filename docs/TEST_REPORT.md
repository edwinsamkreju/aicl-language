# Prototype test and measurement report

Recorded 22 November 2026.

- Runtime: Python 3.13.5.
- Local automated suite: **20 tests passed** using `PYTHONPATH=src pytest -q`.
- CLI smoke tests: `aicl check` and `aicl run` passed through `python -m aicl`.
- Compact patch end-to-end: `aicl patch` accepted the `.aiclp` example; the patched function returned `21` for input `7`.
- Patch safety: stale base hashes, unknown nodes, invalid replacement types, and overlapping edits are rejected before write.
- Patch representation microbenchmark: compact AICL Patch Text was **126 characters** versus **192 characters** for an equivalent minified JSON fixture, a **34.38% character reduction** for this single example.
- Token benchmark: **not measured** because `tiktoken` was unavailable in the offline authoring environment. Character count is not token count.
- GitHub Actions: configured for Python 3.11 and 3.12; hosted runs have not yet been verified.

The character comparison is illustrative, not a general efficiency claim. No claim is made about full task-workflow token savings, correctness parity across a large corpus, runtime performance, or production security.
