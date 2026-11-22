# Prototype test report

Test run performed in the authoring environment on 22 November 2026.

- Python: 3.13.5
- Automated tests: **9 passed** (`PYTHONPATH=src pytest`)
- Packaging/CLI: editable installation succeeded with the environment's installed build tooling; `aicl check` and `aicl run` smoke tests passed.
- Patch workflow: hash-guarded patch applied, candidate type-checked, and patched function returned the expected value.
- Token benchmark: **not run** because the optional `tiktoken` package was not installed in the offline authoring environment. No token-efficiency result is claimed.

The GitHub Actions workflow is configured for Python 3.11 and 3.12; those hosted runs have not yet occurred.
