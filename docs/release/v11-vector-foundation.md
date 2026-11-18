# Pinned vector candidate foundation

**Date:** 2026-11-18  
**Scope:** Stage B candidate retrieval for the fictional local stack.

The database remains PostgreSQL 16 Alpine and now builds pgvector from its official v0.8.7 tag. Migration 009 enables the extension and adds a 64-dimensional vector, profile identifier, and vector checksum beside each exact source chunk. Existing non-revoked chunks are backfilled during migration. Seed and governed intake use the same indexing path; revoked sources retain no chunks.

The first profile, `token-set-sha256-64-v1`, hashes English alphanumeric tokens into a deterministic binary vector. It is a **retrieval plumbing baseline**, not a semantic embedding model. It requires no model download and does not justify answer-quality claims. A later embedding adapter must use a new profile and a full rebuild. Vector search ranks only chunks that pass the same tenant, role, valid-time, recorded-time, supersession, revocation, and optional source-scope predicates as full-text search. The query holds the evidence read lock and verifies returned source/chunk/vector checksums and exact text offsets. Ranking is an exact scan of the authorized scope; an approximate cross-tenant index is intentionally absent.

`tools/rebuild_index.py` now detects missing or changed vectors and profiles in its dry run, then repairs them only with `--apply`. The live v11 gate exercises temporal and tenant isolation, revoked denial, checksum rejection after vector tampering, and repair. It runs after the existing search and rebuild gates in CI and demo preflight.

The interactive demo still uses its bounded source-version resolver. This vector function returns candidates; it does not generate or verify claims. Hybrid fusion, a pinned semantic model, per-stage telemetry, broader ingestion, and the 100+ independently reviewed evaluation remain open. Local Docker was unavailable during implementation; the first fresh-stack CI run is the live verification gate. Before restarting an existing persistent database with a newly built image, retain a backup of any local demo work.
