# Full-text foundation checkpoint

**Date:** 2026-10-27
**Scope:** First Stage B retrieval slice. The v0.6 demo resolver remains the answer baseline; this is not a hybrid or model-generated answer release.

## Implemented

- Migration `008_full_text_chunks.sql` backfills exact text for existing source chunks and adds an English PostgreSQL full-text index. New chunks persist their exact text alongside offset and SHA-256.
- `api.app.retrieval.full_text_chunks` ranks matched chunks while applying tenant, role, valid-time, recorded-time, supersession, revocation, and optional source filters in the database query. It checks the returned chunk against its stored source text and hashes before exposing it to a caller.
- The retrieval call holds a shared tenant evidence lock, so a concurrent revocation cannot commit between candidate selection and return.
- Seed loading skips revoked source chunks, and migration clears any legacy revoked chunks before a missing-index backfill.
- The live check covers historical correction, valid-time expiry, tenant and role isolation, revoked evidence, exact offsets, and empty source scope. It is included in CI and demo preflight.

## Verification

The static suite passed locally. The fresh-stack [CI run](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40386335864) passed the seed, worker, historical answer suites, and the full-text search check at commit `d752ac7`, including the zero-chunk assertion for revoked seed evidence. The foundation smoke derives its expected migration count from the migration files and counts only non-revoked sources as indexable. Local Docker was unavailable for a second live run.

## Still open in Stage B

pgvector and pinned embedding/reranking profiles, hybrid fusion, artifact storage abstraction, model/config registry, stage telemetry, resumable ingestion, and a full index rebuild procedure remain. Search hits are candidate evidence only; approval and claim verification are separate work in Stage C. No public search endpoint or new answer behavior is claimed here.
