# ADR-006: Human approval boundary

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Treat extracted claims as candidates. Only a reviewed decision contract with named owner and approver may represent an approved decision.

## Consequences and verification

Extraction may accelerate review but cannot silently create authority. Test draft/rejected/expired/approved state transitions and self-approval policy.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
