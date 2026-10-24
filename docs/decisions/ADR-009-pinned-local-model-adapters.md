# ADR-009: Pinned local model adapters

**Status:** accepted for the initial local design, 2026-10-24. Revisit after measured evaluation.

## Decision

Use local, version-pinned embedding, reranking, and optional generation adapters behind interfaces; keep a deterministic structured-answer baseline.

## Consequences and verification

No model download is committed. Record model checksum, prompt/config version, memory, and latency; replace only after slice-level evaluation gain.

This is a design decision. Its control and performance claims remain unverified until the named tests run.
