# Authorized hybrid candidate baseline

**Date:** 2026-11-18  
**Scope:** First Stage C retrieval slice for the fictional local stack.

`hybrid_candidate_chunks` fuses PostgreSQL full-text and the pinned token-set vector ranks with reciprocal-rank fusion. Both ranks are computed inside one database snapshot after tenant, role, valid-time, recorded-time, supersession, revocation, source-scope, and embedding-profile predicates. The evidence read lock covers ranking and verification. Returned candidates are checked against exact source/chunk offsets and checksums, including the stored vector.

This is an exact scan of the authorized scope. It is suitable for the small fictional corpus, not a measured large-corpus search design. The token-set vector is lexical and deterministic, not a semantic model. The function returns candidates only; the interactive answer resolver remains unchanged. It does not infer decision approval, generate claims, or make unsupported citations authoritative.

The live gate compares lexical, vector, and fused candidates for a historical record, its correction, and a Lumen source. It also checks cross-tenant source-scope denial, empty source scope, and revoked-source denial. The [fresh-stack CI run](https://github.com/Preethamreddy29/decisiontrace/actions/runs/44351410245) passed this gate and all previous demo, index, outbox, and restore checks. A broader retrieval evaluation, semantic model, reranking, structured generation, deterministic claim verifier, latency/memory report, and reviewed 100+ question set remain open.
