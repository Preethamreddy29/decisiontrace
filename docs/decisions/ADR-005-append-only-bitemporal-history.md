# ADR-005: Append-only bitemporal history

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Store product-valid intervals separately from recorded timestamps and append corrections rather than rewriting earlier versions.

## Consequences and verification

Queries explicitly choose valid date and recorded-as-of cutoff. Test correction, supersession, leap-day, timezone, and half-open boundary fixtures.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
