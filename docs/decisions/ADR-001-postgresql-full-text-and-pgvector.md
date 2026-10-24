# ADR-001: PostgreSQL full-text and pgvector

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Use one PostgreSQL database with full-text search and pgvector for local hybrid retrieval. A separate vector service adds operational cost before the corpus justifies it.

## Consequences and verification

Keep tenant and permission predicates in the same database query. Measure retrieval and index growth on the 100-question corpus; revisit only if evidence shows a bottleneck.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
