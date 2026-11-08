# DecisionTrace implementation plan

**Updated:** 2026-11-08. The entries below distinguish the bounded fictional demo from the full portfolio v1 gates. See the [portfolio completion plan](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/05_DECISIONTRACE_COMPLETION_PLAN.md) for the full ordered work and exit evidence.

| Milestone | Current evidence | Gate status |
|---|---|---|
| Phase 0 — product and corpus | MIT license, fictional six-month corpus, 14 source versions, 25 labeled seed questions, checksummed manifest | Seed gate passed. The later 100+ independently reviewed evaluation set remains open. |
| Phase 1 — contracts and threats | Temporal model, API/event drafts, ten ADRs, threat-to-test map | Design gate passed; contracts and threat tests must continue to track runtime changes. |
| Phase 2 — local foundation | PostgreSQL/API/worker/web Compose, checked migrations, seed, readiness, CI, authorized full-text chunks and index rebuild | Local core gate passed. pgvector, model/artifact adapters, full ingestion states, and telemetry remain. |
| Phase 3 — temporal cited answer | Interactive v0.6 fictional demo, exact section citations, independent decision review, bounded conflict/abstention, draft holdout diagnostic | Bounded preview works. General hybrid/model answer pipeline, independent label review, and a real OIDC issuer/browser test remain; full product gate open. |
| Phase 4–6 — governed MVP, security, evaluation | File/push intake, correction lineage, three typed downstream watches, author revocation, local outbox/replay, concurrency and restore checks | Partial. Extraction review, semantic drift, broader adapters, authorization/failure matrix, reviewed 100+ cases, latency/memory reports remain. |
| Phase 7–9 — release and proof | Demo guide and versioned preview release notes | Open. Clean-host restore, rollback, exact release images, tagged v1, case study, and economics remain. |

## Current build sequence

1. Finish Stage A with a manual UI walkthrough and clean local stack run. CI already proves current event handling, concurrent revocation, and a same-server restore of an API-revoked source.
2. Complete Stage B from the [full-text foundation](release/v08-full-text-foundation.md) and [index rebuild](release/v10-index-rebuild.md): pinned pgvector and local model profiles, source/artifact storage, stage traces, and resumable ingestion.
3. Deliver Stage C hybrid retrieval, structured generation, deterministic claim/citation verification, and measured comparison against the current resolver.
4. Complete the governed source/review breadth, evidence-grounded drift and health, the security and evaluation gates, then the clean-host release drills and v1 proof.

The maintainer's review of [20 draft labels](release/v05-review-packet.md) is still needed to close the bounded Phase 3 answer-quality gate. A real identity-provider test needs issuer, audience, JWKS, tenant/role mapping, test identities, and browser token flow. The local demo credentials are only for fictional loopback testing.

## RuleTwin dependency

DecisionTrace develops in its own repository and database while RuleTwin continues separately. An integrated demo requires a stable versioned RuleTwin evidence contract, tenant/identity semantics, fixtures, and passing consumer tests. Standalone DecisionTrace work does not require that integration.

The [progress log](progress.md) records each verified increment and its remaining limits. Historical release notes remain in [docs/release](release/).
