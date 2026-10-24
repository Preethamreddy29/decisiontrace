# DecisionTrace Implementation Plan

**Updated:** 2026-10-24. Estimates and phases are gates, not completion claims.

| Milestone | Deliverable | Exit evidence |
|---|---|---|
| Phase 0: product and corpus — passed | Charter, synthetic six-month history, 25 labeled seed questions, corpus manifest and MIT license | `python tools/validate_corpus.py` validates 14 source versions, 25 labels, permission/temporal references, and SHA-256 manifest. No model results claimed. |
| Phase 1: contracts and threats — design gate passed | Temporal invariants, conceptual ERD, versioned API/event schemas, permission/deletion model, ten ADRs, threat-to-test map | See `docs/release/phase1-design-gate.md`. Contracts validate; implementation tests remain pending. |
| Phase 2: local foundation — passed | Separate API/web/worker/database, migrations, seed loader, checks, local startup | Local Docker smoke, web build, readiness failure/recovery, and worker ping pass. Clean GitHub CI and checkout evidence are recorded in `docs/release/phase2-foundation-gate.md`. |
| Phase 3: standalone demo — curated preview available, full gate open | One-tenant temporal cited-answer slice, correction, supersession, 25 evaluated questions | The curated synthetic UI and 25 seed-prompt status/citation checks pass locally. See `docs/release/phase3-demo-preview.md` for scope and remaining product gate. |
| Phase 4–6: v1 breadth and hardening | More source types, two-tenant permissions, drift, 100+ gold set, failure/security/evaluation | Permission, citation, temporal, abstention, and injection gates pass on versioned fixtures. |
| Phase 7–9: release and proof | Restore/reindex, rollback, exact release smoke, tagged local v1, demo/case study | Release evidence is reproducible on named hardware. |

## Parallel RuleTwin development

The portfolio's original sequence deferred DecisionTrace until RuleTwin v1. The maintainer requested DecisionTrace work in parallel on 2026-10-23. Standalone DecisionTrace work uses synthetic evidence and its own repository/database. Integration waits for a stable RuleTwin evidence contract, sample fixtures, authentication/tenant semantics, and consumer contract tests. The first DecisionTrace demo must not depend on RuleTwin being finished.

## Next work

Harden the Phase 3 preview into the contracted query/citation product flow, add independent evaluation and authorization, then proceed to Phase 4–6 breadth. Progress and open gaps are tracked in `docs/progress.md`.
