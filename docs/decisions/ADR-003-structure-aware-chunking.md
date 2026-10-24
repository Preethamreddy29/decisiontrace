# ADR-003: Structure-aware chunking

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Parse documents into stable sections first, then bounded chunks keyed by source version, section path, and chunker version.

## Consequences and verification

Unrelated section edits should not renumber all chunks. Test stable IDs, heading context, and citation spans on Markdown, transcript, and JSON fixtures.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
