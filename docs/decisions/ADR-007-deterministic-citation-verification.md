# ADR-007: Deterministic citation verification

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Resolve citation IDs on the server and check existence, tenant, permission, time, scope, and claim support before display; remove unsupported claims or abstain.

## Consequences and verification

A local generator is optional for the first slice. Test invented, revoked, wrong-tenant, wrong-time, and irrelevant citations.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
