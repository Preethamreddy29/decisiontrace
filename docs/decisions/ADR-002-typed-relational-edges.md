# ADR-002: Typed relational edges

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Store decision and evidence relationships as typed, tenant-scoped relational rows rather than a graph database.

## Consequences and verification

The first workload is bounded provenance and drift traversal. Test cycle handling and query depth; revisit if measured traversals become dominant.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
