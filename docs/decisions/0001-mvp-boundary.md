# ADR 0001: MVP boundary and implementation language

- Status: accepted for the research prototype
- Date: 2026-11-22

## Context

The AICL project report recommends proving token efficiency on a compact, narrow language before investing in a general-purpose compiler, runtime, or custom model vocabulary. The first milestone should support an end-to-end create, parse, verify, run, patch, and test loop.

## Decision

This repository starts with a dependency-free Python reference implementation of AICL-C 0.1. It includes a small typed expression language, deterministic typed JSON IR, stable path-derived node identifiers, hash-guarded source patches, a bounded reference interpreter, conformance tests, and an optional tokenizer comparison script.

Python is an implementation vehicle for the prototype, not the target runtime or the language design. The canonical IR remains the intended semantic source of truth.

## Deliberately deferred

- Full module/import system and package registry.
- Records, generics, tensors, shape polymorphism, async, and streams.
- Non-pure effects, capability grants, host calls, and filesystem/network access.
- Native, MLIR, StableHLO, LLVM, and WebAssembly backends.
- Binary IR encoding, native-token profile, formatter, language server, and hosted service.
- Final project licence and trademark/name clearance.

## Consequences

The prototype is runnable and testable on a standard Python installation, but it is not a secure general-purpose runtime, production compiler, or evidence of token savings. Any token claim must use declared tokenizers, equivalent tasks, success tests, and full repair-loop accounting.
