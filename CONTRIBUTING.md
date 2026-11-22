# Contributing

Copyright © 2026 Edwin Sam K Reju. All rights reserved.

1. Keep the language specification, parser, type checker, interpreter, and tests in sync.
2. Add a conformance test for every syntax or semantic change.
3. Preserve deterministic IR output and hash-guarded transactional patch behaviour.
4. Do not introduce ambient host access. Effects and capabilities require a separate design decision and security review.
5. Do not claim token savings from source length. Use the benchmark harness with an identified tokenizer and report task success and retries separately.

Run the test suite with `python -m pytest`.
