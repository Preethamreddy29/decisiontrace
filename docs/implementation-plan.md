# DecisionTrace Implementation Plan

**Updated:** 2026-10-25. Estimates and phases are gates, not completion claims.

| Milestone | Deliverable | Exit evidence |
|---|---|---|
| Phase 0: product and corpus — passed | Charter, synthetic six-month history, 25 labeled seed questions, corpus manifest and MIT license | `python tools/validate_corpus.py` validates 14 source versions, 25 labels, permission/temporal references, and SHA-256 manifest. No model results claimed. |
| Phase 1: contracts and threats — design gate passed | Temporal invariants, conceptual ERD, versioned API/event schemas, permission/deletion model, ten ADRs, threat-to-test map | See `docs/release/phase1-design-gate.md`. Contracts validate; implementation tests remain pending. |
| Phase 2: local foundation — passed | Separate API/web/worker/database, migrations, seed loader, checks, local startup | Local Docker smoke, web build, readiness failure/recovery, and worker ping pass. Clean GitHub CI and checkout evidence are recorded in `docs/release/phase2-foundation-gate.md`. |
| Phase 3: standalone demo — interactive v0.5 available, full product gate open | Bounded decision questions; temporal and section citations; governed text/file/connector source versions; decision draft and independent approval; optional external-token verification; draft evaluation set | v0.5 adds upload, push-connector revision tracking, bounded persisted chunks, and an OIDC verifier. The 20-case diagnostic passes locally but requires independent human label review; a real issuer integration is not yet exercised. See `docs/release/v05-identity-intake-evaluation.md`. |
| Phase 4–6: v1 breadth and hardening — v0.6 increment underway | More source types, two-tenant permissions, reviewed downstream change watches, semantic drift, 100+ gold set, failure/security/evaluation | v0.6 adds version-change review and source revocation; full phase gate remains open. Permission, citation, temporal, abstention, and injection gates must pass on expanded versioned fixtures. |
| Phase 7–9: release and proof | Restore/reindex, rollback, exact release smoke, tagged local v1, demo/case study | Release evidence is reproducible on named hardware. |

## Parallel RuleTwin development

The portfolio's original sequence deferred DecisionTrace until RuleTwin v1. The maintainer requested DecisionTrace work in parallel on 2026-10-23. Standalone DecisionTrace work uses synthetic evidence and its own repository/database. Integration waits for a stable RuleTwin evidence contract, sample fixtures, authentication/tenant semantics, and consumer contract tests. The first DecisionTrace demo must not depend on RuleTwin being finished.

## Next work

Obtain independent review of the 20 draft labels and exercise the OIDC configuration against a real issuer before closing the full Phase 3 product gate. For Phase 4, broaden source adapters and the reviewed question set, add candidate extraction review, and extend change watches toward evidence-grounded semantic drift and a health dashboard. RuleTwin integration follows its stable evidence contract. Progress and open gaps are tracked in `docs/progress.md`.
