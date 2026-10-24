# ADR-008: Tombstone-first deletion and lineage

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Commit an authorization tombstone before asynchronous removal from chunks, embeddings, links, caches, and artifacts.

## Consequences and verification

Cleanup is retried idempotently and auditable. Test immediate denial during partial failure and eventual complete deletion.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
