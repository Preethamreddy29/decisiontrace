# ADR-010: Permission filtering before retrieval

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Derive tenant and role on the server and apply permission/temporal filters in storage before candidates reach reranking or generation.

## Consequences and verification

Cache keys include permission and version context. Test that unauthorized candidates never appear in traces, contexts, answers, or exports.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
