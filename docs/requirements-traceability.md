# DecisionTrace Requirements Traceability

**As of 2026-10-24:** Phase 1 design coverage and Phase 2 foundation startup are validated. Product behavior and release proofs below remain open.

| ID | Requirement | Design location | Required implementation proof |
|---|---|---|---|
| DT-01 | Versioned local source ingestion with checksum, type, size, tenant, origin, and lineage | `data-model.md`; `contracts/openapi.json` | Duplicate, malformed, oversized, wrong-tenant, and tamper tests. |
| DT-02 | Stable sections/chunks from Markdown, transcript, and JSON | ADR-003; `data-model.md` | Unrelated edit leaves other chunk IDs stable. |
| DT-03 | Human-reviewed decision contracts | ADR-006; API review route | Draft/rejected/self/stale approval rejected. |
| DT-04 | Separate valid and recorded time with correction and supersession | `temporal-model.md`; ADR-005; corpus Q01–Q09 | Boundary and historical query fixtures pass. |
| DT-05 | Authorized keyword/vector hybrid retrieval | ADR-001/004/010; `threat-to-test.md` | Unauthorized candidate never leaves storage; retrieval slices measured. |
| DT-06 | Exact claim-level citations and abstention | ADR-007; answer/citation schemas; Q22–Q25 | Invented, revoked, irrelevant, wrong-time/tenant citations fail. |
| DT-07 | Contradiction and drift as reviewable findings | Typed relations; drift routes; Q15–Q18 | Finding links both sides; draft cannot become authority. |
| DT-08 | Deletion/revocation through lineage | ADR-008; deletion API/event; retention proposal | Immediate denial and eventual cleanup under crash/retry. |
| DT-09 | Local model/pipeline version recording | ADR-009; answer/evaluation schemas | Same pinned tuple reproducible; mixed index rejected. |
| DT-10 | Audit and outbox on protected mutations | `data-model.md`; event schema | No acknowledged action without audit/outbox record. |
| DT-11 | Multi-tenant permission isolation | ADR-010; `threat-to-test.md`; Q10/Q11/Q23 | Full source, query, citation, cache, export, trace matrix passes. |
| DT-12 | Reproducible local demo and evaluation | `implementation-plan.md`; corpus manifest | Clean setup, 25-case first slice, later 100+ gold and named-hardware report. |

The Phase 1 design gate requires each critical row to have a concrete contract and planned proof. Phase 2 validates the clean-start foundation only; the product-specific implementation proofs in this table remain pending for Phase 3 and later gates.
