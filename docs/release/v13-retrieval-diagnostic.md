# Candidate retrieval timing diagnostic

**Date:** 2026-11-19
**Scope:** Local synthetic Stage B/C candidate measurement; no answer-quality claim.

`python -m tools.bench_retrieval` runs the 25 seed questions through full-text, pinned token-set vector, and exact rank-fused candidate paths. Each case and path gets one warmup call and three timed calls at limit five. The JSON report includes the seed file SHA-256, search/profile versions, PostgreSQL/pgvector versions, chunk count, machine profile, call count, returned-candidate count, and P50/P95/mean/max wall time. It does not score retrieval relevance, citations, or generated answers.

The first local run exposed that `plainto_tsquery` required every normalized question term in one chunk and returned **zero full-text candidates** across 75 measured calls. The full-text path now ORs PostgreSQL-normalized lexemes for candidate recall, then ranks with `ts_rank_cd`. The hybrid candidate path uses the same query. Authorization still occurs in the SQL before candidate ranking; an unrelated authorized candidate may now be returned, so the tenant and revocation tests assert denial with explicit source scopes. The answer path remains unchanged.

After that correction, the local persistent-volume preflight and targeted search gates passed on PostgreSQL 16.15, pgvector 0.8.7, WSL2 x86_64 with 12 reported logical CPUs and 18 indexed chunks. For 75 measured calls per path, full-text returned 228 candidates with P50 15.457 ms and P95 24.117 ms; token-set vector returned 345 with P50 15.086 ms and P95 26.437 ms; rank fusion returned 345 with P50 19.057 ms and P95 35.374 ms. These are one machine's diagnostic measurements and include connection overhead. They are not a latency SLA or evidence that candidates support the answer.

The original persistent database was backed up before migration; the local preflight passed its seed, versioned workflow, tenant, revocation, index, candidate, and restore checks. The manual browser walkthrough confirmed the local sign-in, 10 May answer, and exact source drill-down. A reviewed retrieval relevance set, semantic embedding profile, per-stage resource metrics, and retrieval-backed claim verification remain open.
