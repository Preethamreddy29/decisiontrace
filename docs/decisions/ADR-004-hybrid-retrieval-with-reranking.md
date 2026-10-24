# ADR-004: Hybrid retrieval with reranking

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Combine permission-filtered keyword and vector candidates using reciprocal-rank fusion, then rerank only authorized candidates with a pinned local model.

## Consequences and verification

Record candidate lists and stage timings. Compare keyword-only, vector-only, hybrid, and reranked variants on a frozen gold set.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
