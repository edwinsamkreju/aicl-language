# ADR 0002: node-addressed patches and compact patch text

- Status: experimental
- Date: 2026-11-22

## Context

The prototype's original patch format replaced a whole function body. That is often wasteful when a model needs to modify one literal, operand, or call argument. AICL's canonical IR already exposes path-derived node IDs, so these IDs can address local edits.

## Decision

Add two patch operations:

- `replace_body`: retain the existing whole-function-body replacement.
- `replace_node`: replace one expression addressed by its canonical base-module node ID.

Add an experimental line-oriented patch serializer named AICL Patch Text 0.2:

```text
aicl-patch 0.2
base sha256:<full canonical module hash>
node scale n:scale:body/right = 3
```

The source file is changed only after the complete candidate parses and type-checks. Full base hashes are mandatory. Unknown nodes, stale hashes, duplicate edits, and overlapping ancestor/descendant edits are rejected. Disjoint node edits in the same function can be combined.

## Evidence and limitations

For one illustrative edit, the compact text fixture is 126 characters, compared with 192 characters for an equivalent minified JSON patch. This is a character-count microbenchmark only. The optional tokenizer script should be used with a named tokenizer; full agent workflows must be benchmarked before claiming token savings.

Node IDs are path-based within a particular canonical base version. They are not promised to remain stable through arbitrary structural rewrites. The base hash prevents applying a patch to an unintended base.

## Consequences

Agents can express fine-grained source changes without resending a complete function body. The implementation adds a compact serialization format but does not yet provide remote context retrieval, binary patch packets, semantic merge/conflict resolution, or durable graph identities across versions.
