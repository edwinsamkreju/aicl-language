# AICL — AI-First Compact Language

**A research-led prototype of a compact, typed programming representation designed for AI coding agents.**

Copyright © 2026 Edwin Sam K Reju. All rights reserved. See [COPYRIGHT.md](COPYRIGHT.md).

AICL is being designed around an AI-first execution loop: agents inspect small typed context slices, propose hash-guarded semantic edits, and verify the result through machine-readable interfaces. Human-readable source is a secondary debugging and review surface, not the centre of the workflow.

AICL separates model-facing compact syntax (**AICL-C**) from compiler-facing canonical typed representation (**AICL-IR**). The repository contains an AICL 0.1 language prototype, experimental **AICL Patch Text 0.2**, and **AICL Agent Protocol 0.1** for bounded context retrieval, verification, and patch application.

> **Status:** early research prototype. Not a production compiler or secure general-purpose runtime. Token-efficiency claims for complete AI programming workflows have not been demonstrated.

## Quick start

Requires Python 3.11 or later.

~~~bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
python -m pip install pytest
pytest
~~~

Check and run an example:

~~~bash
aicl check examples/clamp.aicl
aicl run examples/clamp.aicl --function clamp --args '[15, 0, 10]'
~~~

Expected output: **{"result": 10}**.

## Canonical IR machine transport

AICL-IR 0.1 has a language-neutral JSON Schema contract at [spec/aicl-ir-0.1.schema.json](spec/aicl-ir-0.1.schema.json). The CLI can emit whitespace-minimized canonical JSON or only the content hash:

~~~bash
aicl ir examples/clamp.aicl --compact
aicl ir examples/clamp.aicl --hash-only
~~~

The compact output has identical JSON semantics to the pretty representation. The module hash is SHA-256 over canonical JSON of the `ir` object. This is a versioned interchange contract, not yet a binary encoding or a second-language implementation.

## AI-first agent interface 0.1

The agent interface is the preferred automation surface. It uses one JSON request per line on stdin and emits exactly one compact JSON response per request on stdout. It is designed for tool adapters and autonomous coding loops, not interactive human use.

Inspect the module signature index without sending function bodies:

~~~bash
printf '%s\n' '{"protocol":"aicl-agent/0.1","op":"inspect","target":"module"}' | aicl agent examples/clamp.aicl
~~~

Request only one function's typed IR tree:

~~~bash
printf '%s\n' '{"protocol":"aicl-agent/0.1","op":"inspect","target":"function","name":"clamp"}' | aicl agent examples/clamp.aicl
~~~

Request only one expression subtree:

~~~bash
printf '%s\n' '{"protocol":"aicl-agent/0.1","op":"inspect","target":"node","id":"n:clamp:body/right"}' | aicl agent examples/clamp.aicl
~~~

Run a structured verification request:

~~~bash
printf '%s\n' '{"protocol":"aicl-agent/0.1","op":"check"}' | aicl agent examples/clamp.aicl
~~~

Apply a patch through the same interface. The patch is checked against the exact canonical module hash and the candidate module is type-checked before an atomic file replacement:

~~~bash
python - <<'PY' | aicl agent examples/patchable.aicl
import json
from aicl.ir import module_hash
from aicl.syntax import parse_module
from pathlib import Path
path = Path("examples/patchable.aicl")
base = module_hash(parse_module(path.read_text(encoding="utf-8")))
patch = f"aicl-patch 0.2\nbase {base}\nnode scale n:scale:body/right = 3\n"
print(json.dumps({"protocol": "aicl-agent/0.1", "op": "patch", "patch": patch}))
PY
~~~

Supported operations are inspect (module, function, or node), check, and patch. A process accepts multiple JSONL requests. Errors are structured JSON responses with stable error codes; a non-zero process exit code indicates that at least one request failed. The request contract is [machine-readable](spec/aicl-agent-0.1.schema.json); the implementation is in [src/aicl/agent.py](src/aicl/agent.py).

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

The important AI-efficiency improvement is reducing the amount of code an agent must resend for a small edit. An agent can target an expression by its IR node ID:

~~~
aicl-patch 0.2
base sha256:<full canonical module hash>
node scale n:scale:body/right = 3
~~~

The patch engine checks the full base hash, verifies that the addressed node belongs to the named function, rejects overlapping edits, applies operations transactionally, and type-checks the complete candidate before writing it.

Run the patch example:

~~~
aicl patch examples/patchable.aicl examples/patch_scale_node.aiclp
~~~

See [the patch grammar](spec/aicl-patch-0.2.ebnf) and [the working example](examples/patch_scale_node.aiclp).

## Existing measurements

The 100-task paired corpus measured 22.59% fewer source characters, 5.88% fewer source tokens, and 2.06% fewer tokens for shared prompt plus source on that fixed narrow corpus. These counts do not measure model-generated completions or complete agent workflow usage.

The AICL reference interpreter was slower than direct CPython calls in the recorded diagnostic. This is a Python-hosted AST interpreter comparison, not a native compiler comparison. See [the full benchmark protocol](docs/EQUIVALENT_TASK_BENCHMARK.md) and [test report](docs/TEST_REPORT.md).

## Live-agent experiment framework

The live-agent A/B protocol, request-level trace schema, deterministic 10-task/two-trial pilot, and trace analyzer are implemented. The framework requires actual provider-reported usage for every model request. No live agent comparison has been performed; the analyzer does not invoke a model by itself.

See [the live-agent experiment protocol](docs/LIVE_AGENT_EXPERIMENT.md), [run checklist](benchmarks/live_agent/AGENT_RUN_PROTOCOL.md), and [trace schema](benchmarks/live_agent/trace.schema.json).

## Repository structure

~~~
src/aicl/                 Parser, type checker, typed IR, agent protocol, interpreter, patcher, CLI
spec/                     AICL-C grammar, IR schema, agent request schema, compact patch grammar
examples/                 AICL programs and compact patch example
benchmarks/               Token, patch, equivalent-task and live-agent benchmarks
tests/                    Language, agent protocol, patch, and benchmark tests
docs/                     Benchmark protocol, design decisions, engineering backlog
~~~

## AI-first design constraints

The long-term target is a machine-optimized programming system. The canonical IR and agent protocol should become the primary interface; compact source is a serialization/debugging layer. The next layers are binary canonical IR transport, stable semantic node identities, incremental diagnostics, dependency-aware context retrieval, and compiler lowering. These capabilities are not implemented yet.

AICL-C 0.1 remains a narrow subset: imports, records, generics, tensor shapes, async/streams, non-pure effects, capability grants, host calls, binary IR encoding, native-token vocabulary, compiler lowering, MLIR/StableHLO/LLVM/Wasm backends, and a hardened sandbox are not implemented.

No general AI-efficiency claim is justified until controlled live-agent trials report provider-reported usage, task completion, correctness, retries, tool calls, latency, and cost.

See [ROADMAP.md](ROADMAP.md), [the benchmark protocol](docs/EQUIVALENT_TASK_BENCHMARK.md) and [docs/INITIAL_BACKLOG.md](docs/INITIAL_BACKLOG.md).

## Copyright and licence

**Copyright © 2026 Edwin Sam K Reju. All rights reserved.**

No open-source licence has been selected. The copyright notice does not itself grant permission to copy, modify, distribute, sublicense, or sell this software. See [COPYRIGHT.md](COPYRIGHT.md).

The original project report PDF is intentionally not included in this repository.
