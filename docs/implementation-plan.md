# DecisionTrace Implementation Plan

**Updated:** 2026-10-24. Estimates and phases are gates, not completion claims.

| Milestone | Deliverable | Exit evidence |
|---|---|---|
| Phase 0: product and corpus — passed | Charter, synthetic six-month history, 25 labeled seed questions, corpus manifest and MIT license | `python tools/validate_corpus.py` validates 14 source versions, 25 labels, permission/temporal references, and SHA-256 manifest. No model results claimed. |
| Phase 1: contracts and threats — design gate passed | Temporal invariants, conceptual ERD, versioned API/event schemas, permission/deletion model, ten ADRs, threat-to-test map | See `docs/release/phase1-design-gate.md`. Contracts validate; implementation tests remain pending. |
| Phase 2: local foundation — passed | Separate API/web/worker/database, migrations, seed loader, checks, local startup | Local Docker smoke, web build, readiness failure/recovery, and worker ping pass. Clean GitHub CI and checkout evidence are recorded in `docs/release/phase2-foundation-gate.md`. |
| Phase 3: standalone demo — interactive v0.2 available, full product gate open | New manual-override questions, server-derived demo tenant/role, temporal source selection, exact claim citations, correction/supersession, conflict, abstention | The interactive flow and 14 frozen paraphrases pass locally. See `docs/release/v02-interactive-demo.md`; production identity, independent review, and broader product behavior remain open. |
| Phase 4–6: v1 breadth and hardening | More source types, two-tenant permissions, drift, 100+ gold set, failure/security/evaluation | Permission, citation, temporal, abstention, and injection gates pass on versioned fixtures. |
| Phase 7–9: release and proof | Restore/reindex, rollback, exact release smoke, tagged local v1, demo/case study | Release evidence is reproducible on named hardware. |

## Parallel RuleTwin development

The portfolio's original sequence deferred DecisionTrace until RuleTwin v1. The maintainer requested DecisionTrace work in parallel on 2026-10-23. Standalone DecisionTrace work uses synthetic evidence and its own repository/database. Integration waits for a stable RuleTwin evidence contract, sample fixtures, authentication/tenant semantics, and consumer contract tests. The first DecisionTrace demo must not depend on RuleTwin being finished.

## Next work

Expand beyond the v0.2 manual-override domain with governed ingestion/review, production identity, and an independently reviewed evaluation set before the full Phase 3 product gate. RuleTwin integration follows its stable evidence contract. Progress and open gaps are tracked in `docs/progress.md`.
