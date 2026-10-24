# Phase 1 Threat-to-Test Map

**Status:** planned controls and tests; none is implemented or passed.

| Threat | Required control | Release-blocking test |
|---|---|---|
| Cross-tenant source or answer access | Server-derived tenant/role context; tenant predicate before retrieval; object authorization on citation open/export | Cedar IDs in Lumen paths, filters, citations, cache, exports, traces, and model context return no data. |
| Permission revoked after indexing | Permission version in query/cache context; immediate deny at source and chunk lookup | Revoke source between indexing and query; no candidate reaches reranker or generator. |
| Deleted source remains retrievable | Transactional tombstone before async cleanup; lineage-based invalidation | Delete while query is in flight and after cache warmup; no answer or citation can expose it. |
| Forged provenance or tampered source | Checksum, origin/tenant/type validation, immutable source version | Change source bytes after manifest approval; ingestion fails or creates a new reviewed version. |
| Prompt injection in uploaded text | Treat source as quoted data; no authority/tool access; deterministic output verification | Inject instructions to reveal another tenant or invent a citation; authorization and verifier reject. |
| Unsupported answer claim or fake citation | Server-resolved citation IDs and per-claim checks; abstain on insufficient support | Generated unknown, wrong-time, wrong-scope, or unrelated citation cannot be displayed as a valid claim. |
| Correction confused with supersession | Typed relation and distinct valid/recorded histories | 10 May as-known, 10 May valid-now, 19 May, and 20 May fixtures return their distinct expected decisions. |
| Unreviewed extraction becomes authoritative | Human review state gate, approver recorded, immutable approved version | Draft or rejected contract cannot answer an authoritative policy query. |
| Parser bomb/path traversal | Type/size limits, bounded parser, safe artifact paths, no archives in v1 | Oversized, malformed, and traversal filenames are quarantined without writing outside storage. |
| Sensitive content in logs/model traces | IDs and timings by default; redaction; local-only model endpoint | Controlled secret fixture never appears in logs, metrics, traces, or error payloads. |
| Worker crash/duplicate ingestion | Idempotent stage checkpoints and outbox/lease recovery | Crash at each stage and replay duplicate source checksum; one logical version and visible failure state. |
| Index/model version mismatch | Pin parser/chunker/embedding/reranker/prompt/index versions per run | Mixed index versions fail closed or use a complete compatible index with an explicit label. |

No row may be marked passed without a test run against a named build and corpus manifest. Security and temporal failures block release even if average answer quality improves.
