# DecisionTrace implementation reference

**Status date:** 2026-11-20
**Code baseline:** DecisionTrace main code at [3ac9fb7](https://github.com/Preethamreddy29/decisiontrace/commit/3ac9fb79b6cd8f8135c42f5147daa919912ddca0), with [passing main CI](https://github.com/Preethamreddy29/decisiontrace/actions/runs/44443407605).
**Scope:** The running v0.6 fictional local demo, the Stage A reliability work, the Stage B retrieval foundation, the first Stage C candidate fusion, and the work required for the portfolio runbook's v1 release.

This is a working implementation map, not a v1 release declaration. The interactive demo answers two fictional policy topics from authorized source versions. Public answers now pass an exact-quotation and authorization gate before storage or return. Internal full-text, token-set vector, and fused retrieval return authorized candidates but do not yet generate the displayed answer. The [portfolio runbook](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/02_DECISIONTRACE_IMPLEMENTATION_RUNBOOK.md) defines the broader product and release gates.

## 1. Product context and the signature demonstration

DecisionTrace reconstructs which product decision applied on a chosen date and what evidence was recorded by a chosen cutoff. It preserves the distinction between a correction to a record and a later approved decision that changes policy. An answer opens the exact version and passage it cites. A human must approve a new decision contract; a source or draft alone cannot become authority.

The fictional Cedar example shows the difference. A query about 10 May with a 10 May recorded cutoff returns the then-known meeting record saying one reviewer. A later recorded correction says two independent reviewers for that earlier period. A superseding approved decision disables overrides from its effective date. The demo also shows missing-evidence abstention, tenant denial, invoice-hold approval, downstream change review, and source revocation. The full guided sequence is in the [demo test guide](demo-test-guide.md).

The demo is bounded to manual overrides and invoice holds. Its source records, identities, and shared passphrase are fictional. It has no general document question answering, autonomous decision approval, or production identity deployment.

## 2. Current running architecture

~~~mermaid
flowchart LR
    Person["Demo user"] --> Web["React + TypeScript UI<br/>localhost:5174"]
    Web --> API["FastAPI<br/>localhost:8001"]
    API --> Auth["Demo token verifier<br/>or optional OIDC verifier"]
    API --> Query["Bounded temporal answer resolver"]
    API --> Workflow["Source, decision, watch<br/>and revocation workflow"]
    CandidateTools["Evaluation and benchmark tools"] --> Search["Internal authorized candidate search<br/>full-text, token-set vector, rank fusion"]
    Query --> PG[("PostgreSQL 16<br/>source and decision versions<br/>chunks, audit, outbox")]
    Workflow --> PG
    Search --> PG
    Migrate["Checked migrations 001–009"] --> PG
    Worker["Local outbox worker"] --> PG
    Preflight["Static checks, live suites,<br/>timing and restore preflight"] --> API
    Preflight --> CandidateTools
    Preflight --> PG
~~~

The [Compose file](../../compose.yaml) starts database, one-shot migration, API, worker, and web services. The database image builds pgvector 0.8.7 on PostgreSQL 16 Alpine. Host ports bind to loopback: web 5174, API 8001, and database 5434. A named volume keeps the fictional database between runs. The API and worker share the same PostgreSQL database; RuleTwin does not.

The two paths after authentication are deliberately distinct:

~~~mermaid
flowchart TD
    Q["POST /v1/query"] --> Scope["Server-derived tenant and role<br/>valid date and recorded cutoff"]
    Scope --> Versions["Authorized source versions<br/>and approved decision evidence"]
    Versions --> Resolver["Bounded topic rules<br/>exact source sentence"]
    Resolver --> Verify["Exact quote, scope<br/>and approval gate"]
    Verify --> Answer["Answered, conflict,<br/>abstain or denied"]
    Answer --> Citation["GET exact source version<br/>fresh authorization and quote check"]

    C["Internal candidate functions"] --> Filter["Tenant, role, time, revocation,<br/>source and profile predicates in SQL"]
    Filter --> FTS["PostgreSQL full-text rank"]
    Filter --> VEC["64D deterministic token-set rank"]
    FTS --> RRF["Exact reciprocal-rank fusion"]
    VEC --> RRF
    RRF --> Candidates["Checksummed candidate chunks"]
~~~

The query request supplies an explicit valid date when needed and a timezone-aware recorded cutoff. The server derives tenant and role from the verified bearer token. Source reads enforce tenant, role, recorded cutoff, supersession, and revocation; the resolver checks effective dates and approved decision evidence. A revoked source is denied even for historical reads. A citation contains source/version IDs, section ID, exact quote, and character offsets; opening it checks access again. See [query.py](../../api/app/query.py), [retrieval.py](../../api/app/retrieval.py), and the [temporal model](../architecture/temporal-model.md).

## 3. Stored data and how the flows work

| Data area | Implemented mechanism | Current boundary |
| --- | --- | --- |
| Tenants and source versions | Tenant, source and version IDs, content SHA-256, kind, origin, role permissions, valid interval, recorded timestamp, supersession and revocation fields. Versions are appended for corrections. | Fictional local sources; no general artifact store or tenant administration. |
| Sections and chunks | Markdown headings, transcript turns, and JSON leaf paths receive deterministic section IDs and exact offsets. Chunks are at most 1,200 characters, checksummed, and linked to one source version. | These chunks power internal candidate search, while the demo answer path reads authorized versions. |
| Decisions | Draft and reviewed versions bind exact evidence-version IDs. A different auditor approves or rejects; stale ETags and self review fail. | No extracted candidate-decision queue or complete v1 contract fields. |
| Watches | Approved decision evidence can be linked to a downstream source as tests, implements, or measures. A new source version becomes needs review; another auditor records drift or alignment with a reason. | Version change is a review prompt, not automatic semantic drift. |
| Requests and audit | Query and mutation idempotency records, audit events, and outbox events are stored in PostgreSQL. Protected mutations write audit/outbox in the same transaction. | Outbox delivery ends at local validation and acknowledgement, with no external subscriber. |
| Candidate index | PostgreSQL English tsvector plus pinned 64D token-set vector and profile/checksum fields on exact chunks. Hybrid fusion uses one authorized database snapshot. | Lexical vector baseline, exact small-corpus scan, no semantic model or production scale claim. |

The nine checked migrations are in [api/migrations](../../api/migrations). Migration 001 creates the base tenant, source, decision, ingestion-job, audit, and outbox tables. Migrations 002–003 add labels, query idempotency, origin, and governed mutation fields. Migrations 004–006 add chunks, connector revision lineage, and watches. Migration 007 versions outbox events. Migration 008 stores chunk text and generated full-text vectors. Migration 009 enables pgvector and adds embedding fields. The migration runner checks recorded checksums before applying pending files.

### 3.1 Source intake and correction

An auditor can create text evidence or upload bounded UTF-8 Markdown, transcript, or JSON. The upload route checks filename, media type, format, byte size, decoded length, and schema. An allowlisted push endpoint accepts checksum-verified remote snapshots with object and revision IDs; it is not a polling connector. The service assigns tenant, actor, source/version IDs, recorded time, and checksum, then parses sections and builds exact chunks. A correction appends a version and preserves earlier recorded history. Source and connector paths are in [workflow.py](../../api/app/workflow.py), [main.py](../../api/app/main.py), [sections.py](../../api/app/sections.py), and [indexing.py](../../api/app/indexing.py).

### 3.2 Review, answer, and citation

A decision draft binds currently permitted evidence versions and an effective interval. An independent auditor reviews that exact draft under If-Match; approval rechecks the evidence. The bounded resolver first filters permitted sources by recorded cutoff, selects the relevant approved decision or fictional fallback, quotes a sentence that exists in the stored source, and returns structured status and citation data. Unsupported questions abstain. Before storage or display, the exact-citation gate checks source/section identity, quote offsets, tenant and role, valid and recorded time, revocation, and any approved decision binding. It checks stored idempotent answers again on retry. The UI opens cited content through a separately authorized source-version route. This is exact-source quotation with bounded topic rules, not general semantic entailment verification. See the [exact citation gate](v14-exact-citation-gate.md).

### 3.3 Change watches and revocation

A watch records the approved decision version, its evidence version, downstream source and baseline version, and relation type. A newer downstream version produces needs_review. An independent auditor can classify it as drift or aligned; the system does not claim the version change itself proves a contradiction. Revocation is author-controlled and takes the same tenant evidence lock used by protected writes and evidence reads. It marks all source versions revoked, deletes their stored chunks, invalidates cached answers, redacts certain retry responses, and records audit/outbox lineage. Raw source rows remain for the local audit; physical erasure, backup retention, and full deletion propagation are future work. See [change_watch.py](../../api/app/change_watch.py), [workflow.py](../../api/app/workflow.py), and the [v0.6 release record](v06-change-watch-revocation.md).

### 3.4 Identity, worker, and repair

Demo mode signs eight-hour bearer tokens with a server-generated secret that changes on restart. It offers fictional Cedar and Lumen accounts. Optional OIDC mode verifies RS256 tokens against configured HTTPS issuer/JWKS, audience, tenant allowlist, and role claim, and disables demo login. Its route has synthetic issuer tests; there is no real-provider browser authorization-code or refresh flow. See [auth.py](../../api/app/auth.py) and [oidc.py](../../api/app/oidc.py).

The worker leases registered version-1 events, marks valid events done, and dead-letters unknown or malformed events. It does not deliver to another service. The safe replay tool addresses eligible dead letters. The chunk rebuild tool is read-only by default; --apply repairs missing or mismatched live chunks/vectors and removes stale revoked chunks under the tenant evidence lock. The restore smoke takes a custom-format PostgreSQL backup, restores to a separate database on the same server, reruns checked migrations, and verifies live/revoked evidence plus audit/outbox records. A clean-host recovery drill is still needed. See [worker.py](../../api/app/worker.py), [rebuild_index.py](../../tools/rebuild_index.py), and [restore smoke](v09-restore-smoke.md).

## 4. What is complete, partial, and pending

The table maps the [DT-01–DT-12 requirements](../requirements-traceability.md) to actual runtime evidence. “Partial” means a bounded local path exists but the runbook's full proof is not met.

| ID | Current state | Completed evidence | Remaining requirement |
| --- | --- | --- | --- |
| DT-01 Source ingestion | Partial | Checksummed, permissioned text/file intake, versioning, push snapshots, input bounds. | Artifact storage, broader adapters, resumable jobs, full malformed/tamper matrix. |
| DT-02 Structure | Partial | Stable Markdown/transcript/JSON section IDs, exact offsets, chunks and repair checks. | Complete adapter fixtures and large-corpus/index compatibility proof. |
| DT-03 Human review | Partial | Draft, separate auditor review, immutable review versions, stale/self-review rejection. | Extraction correction queue and full contract fields/relations. |
| DT-04 Temporal history | Bounded pass | Valid/recorded distinctions, correction and supersession cases in seed/demo tests. | Broader multi-source and independently reviewed temporal evaluation. |
| DT-05 Hybrid retrieval | Partial | Authorized full-text, pinned token-set vector, exact rank fusion, repair and timing diagnostic. | Semantic profile, relevance labels, reranking, scalable index and answer integration. |
| DT-06 Cited answers | Partial | Exact quotes, offsets, section drill-down, conflict/abstain states, and a fail-closed server gate for current claims and cached replies. | Retrieval-backed generation and evaluated support verification for arbitrary generated claims. |
| DT-07 Drift | Partial | Three typed watches and independent drift/alignment review. | Automatic evidence-grounded findings, contradiction rules, health dashboard, precision/recall. |
| DT-08 Revocation/deletion | Partial | Immediate source denial, chunk/cache cleanup, same-server restore proof. | Physical erasure/retention, all artifact/index lineage, crash/retry and clean-host recovery. |
| DT-09 Model versions | Partial | Explicit chunker, search, token-set profile and answer pipeline version strings. | Pinned semantic embedder/reranker/generator, model registry and compatibility enforcement. |
| DT-10 Audit/outbox | Partial | Transactional local audit/outbox, event validation, replay and concurrency tests. | External delivery contract and full failure operations. |
| DT-11 Tenant isolation | Partial | Server-derived tenant/role and bounded source/query/candidate/watch denial tests. | Full route, export, trace, cache and adversarial permission matrix with release threshold. |
| DT-12 Reproducible demo | Bounded pass | One-command local preflight, seed suite, browser walkthrough, fresh CI and restore smoke. | Independently reviewed 100+ set, named-hardware full report, clean-host and tagged release. |

### Build history and evidence

| Increment | Landed behavior | Evidence |
| --- | --- | --- |
| Foundation and preview | Licensed fictional corpus, contracts, checked migrations, Compose, 25 seed questions and bounded answer preview. | [Phase 2 gate](phase2-foundation-gate.md), [preview record](phase3-demo-preview.md). |
| v0.2–v0.4 | Interactive temporal answer/citation flow, governed decision review, structured source sections and second demo topic. | [v0.2](v02-interactive-demo.md), [v0.3](v03-governed-workflow.md), [v0.4](v04-structured-evidence.md). |
| v0.5–v0.6 | Optional synthetic-tested OIDC route, bounded file/push intake, draft holdout, watches, revocation. | [v0.5](v05-identity-intake-evaluation.md), [v0.6](v06-change-watch-revocation.md). |
| Stage A | Versioned local outbox, safe replay, concurrent read/revocation ordering, same-server restore. | [Reliability](v07-outbox-stability.md), [restore](v09-restore-smoke.md). |
| Stage B | Full-text chunks, dry-run-first rebuild, pgvector token-set baseline. | [Full-text](v08-full-text-foundation.md), [rebuild](v10-index-rebuild.md), [vector](v11-vector-foundation.md). |
| Early Stage C | Exact authorized rank fusion and a repeatable candidate timing diagnostic; the diagnostic led to a full-text recall fix. | [Fusion](v12-hybrid-candidates.md), [diagnostic](v13-retrieval-diagnostic.md), [main CI](https://github.com/Preethamreddy29/decisiontrace/actions/runs/44443407605). |
| Exact citation gate | Server checks new and cached bounded answers against current authorized exact evidence; adversarial fixture rejects forged claims and citations. | [Gate record](v14-exact-citation-gate.md). |

The frozen seed corpus has 14 source versions across two tenants and 25 specified questions. Fourteen paraphrases are separate regression checks. The 20-case v0.5 holdout is an agent-authored draft and needs independent label review. A 25-question timing run measured 75 calls per candidate path on one WSL2 machine; its P95 was 24.117 ms full-text, 26.437 ms token-set vector, and 35.374 ms fusion. These are candidate timings, not retrieval relevance, answer accuracy, or an SLA. See the [diagnostic record](v13-retrieval-diagnostic.md).

## 5. Branches, publication, and release identity

### Actual branch state at this snapshot

| Repository and branch | Role and relationship to released code |
| --- | --- |
| DecisionTrace main code baseline at 3ac9fb7 | Published code/demo baseline before this documentation change. The full CI run 44443407605 passed. |
| DecisionTrace codex/stage-b-vector-foundation at fdb0d03 | Historical vector and fusion work branch. Its commits are ancestors of main. |
| DecisionTrace codex/retrieval-benchmark at 354fa79 | Historical diagnostic/search-fix branch. It passed branch CI, then main was fast-forwarded to the same code commit; the later README-only commit is on main. |
| DecisionTrace codex/implementation-reference | Branch for this documentation update, created from main. |
| DecisionTrace codex/citation-verifier | Follow-up branch for the exact citation gate and adversarial test. |
| Portfolio main at 7eeb108 | Published portfolio baseline; it does not yet contain the later DecisionTrace status updates. |
| Portfolio codex/decisiontrace-status at fcc5262 | Earlier status branch, ancestor of the newer portfolio status branch. |
| Portfolio codex/portfolio-ruletwin-sync | Current DecisionTrace completion-plan status branch, based on portfolio main and still separate from it. |

No DecisionTrace Git tag existed when this snapshot was taken. The preview version in the API and documents is a product label, not a tagged release. The portfolio plan is linked from the DecisionTrace README using its status branch; readers of portfolio main alone will not see those later status commits until that branch is integrated.

~~~mermaid
flowchart LR
    DT0["DecisionTrace foundation and v0.6"] --> DTA["Stage A reliability"]
    DTA --> DTB["Stage B full-text, rebuild, vector"]
    DTB --> DTC["Fusion baseline"]
    DTC --> DTD["codex/stage-b-vector-foundation<br/>fdb0d03"]
    DTD --> DTE["codex/retrieval-benchmark<br/>354fa79"]
    DTE --> DTM["main code baseline<br/>3ac9fb7"]
    DTM --> DOC["codex/implementation-reference<br/>this documentation"]
    DOC --> CV["codex/citation-verifier<br/>exact quote gate"]
    PM["Portfolio main<br/>7eeb108"] --> PS["codex/decisiontrace-status"]
    PS --> PP["codex/portfolio-ruletwin-sync<br/>status branch"]
~~~

### Branch and release procedure

The observed DecisionTrace work used focused codex/ branches. The vector and diagnostic commits passed branch CI, were fast-forwarded directly to main, and then passed main CI; their remote branches remain. The portfolio status branch is a separate documentation stream. The portfolio engineering handbook proposes feat/, fix/, docs/ and similar branch names, protected main, and reviewable PR increments. Those proposed branch-protection and PR controls are not established by this history; no PR is claimed for the documented integrations. Future slices should keep code, migrations, tests, and dated evidence in a small task branch, review the exact CI result, and use the handbook PR workflow once it is in place. A pushed branch, seed pass, or preview number does not satisfy a v1 gate. Tag a release only after the frozen corpus/model/schema, security, restore, rollback, and evaluation proof is complete.

## 6. Remaining build sequence and exact exit evidence

The order below follows the [portfolio completion plan](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/05_DECISIONTRACE_COMPLETION_PLAN.md). Work already completed in a stage is stated above; each item here is still required for full v1.

The planned v1 pipeline adds the following stages. It is a target architecture; only the bounded intake, review, indexing, candidate fusion, and exact-quotation gate pieces exist today.

~~~mermaid
flowchart LR
    Sources["Governed sources"] --> Intake["Versioned adapters<br/>resumable ingestion"]
    Intake --> Extract["Candidate claims<br/>and decisions"]
    Extract --> Review["Human correction<br/>and approval"]
    Review --> Index["Authorized full-text<br/>and semantic index"]
    Index --> Fusion["Fusion and reranking"]
    Fusion --> Context["Temporal evidence context"]
    Context --> Generate["Pinned local structured generation"]
    Generate --> Verify["Deterministic claim<br/>and citation verification"]
    Verify --> Result["Answer, conflict<br/>or abstain"]
    Identity["Server-derived identity<br/>and time scope"] --> Index
    Identity --> Verify
    Review --> Audit["Audit and outbox"]
    Verify --> Audit
~~~

1. **Complete Stage B pipeline foundation.** Add an artifact/source storage abstraction and a pinned local semantic embedding profile with model checksum and a compatible full rebuild. Add resumable, idempotent ingestion states and per-stage traces/resources. Build an independently reviewed relevance set, compare keyword/vector/hybrid candidates, and specify a scalable authorized index path. Exit when model/index versions are reproducible, unauthorized candidates never leave storage, an interrupted ingest resumes, and relevance and resource results are recorded.
2. **Complete Stage C answers.** Add reranking, temporal context assembly, structured local generation, evaluated claim-support checks beyond the current exact-quotation gate, and explicit abstention or degraded behavior. Keep the bounded resolver as a measured baseline. Exit when the seed and reviewed cases pass, every claim opens authorized evidence, and invented, revoked, wrong-time, wrong-tenant, or unsupported citations fail closed.
3. **Finish the governed MVP.** Add the remaining PRD, ticket, ADR, test, release and metric adapters; extracted claim/decision suggestions with a human correction queue; complete scope, owner, approver, assumptions, expiry and revisit fields; and the required supports/contradicts/corrects/supersedes/implements/tests/measures relations. Exit with version correction and approval tests for every type and tenant/role checks across source, claim, relation, review, and export paths.
4. **Build evidence-grounded drift and health.** Compare active approved decisions with downstream implementation, tests, releases, metrics and assumptions. Persist findings with both exact evidence sides and let reviewers resolve them. Exit with true/false drift fixtures, version and revocation updates, and reported precision/recall.
5. **Harden identity, privacy and failures.** Test a real OIDC issuer, browser sign-in and refresh once a test provider exists. Complete the permission matrix, injection suite, deletion/retention propagation, worker-crash and model/index outage drills, telemetry redaction, and safe degraded modes. Exit only when hard security gates in the portfolio evidence matrix pass.
6. **Evaluate independently.** Review the 20 draft labels with a person other than the implementer, freeze corrections, and then author and review the separate 100+ case set across temporal, conflict, abstention, drift, permission, and injection slices. Report citation validity, supported-claim rate, temporal and abstention accuracy, retrieval Recall@K/MRR, P50/P95 per stage, and peak memory on named hardware. The runbook targets 100% permission denial and citation validity, at least 0.95 supported-claim rate, at least 0.90 temporal and abstention accuracy, and zero successful release-set injection bypasses. A draft diagnostic does not close these gates.
7. **Release and prove v1.** Freeze exact schema, models, prompts, corpus, gold labels and index manifests. Rehearse prior-tag migration, clean-host backup/restore/reindex and rollback; review licenses/SBOM; build and test a tagged RC, then promote exact images/config to v1. Publish the case study and resource/cost model. Exit with the signature demo reproduced from the tagged release and the evidence matrix linked to exact artifacts.

Two inputs remain outside the current code: independent human approval or corrections for the [20 draft labels](v05-review-packet.md), and a real OIDC test provider with issuer, audience, JWKS, tenant/role claim mapping, and test identities. The user has offered to review labels together; that review is not yet recorded. Standalone DecisionTrace development can continue without either input, but those gates cannot be marked passed.

## 7. RuleTwin and portfolio boundary

DecisionTrace and RuleTwin are separate repositories and databases. RuleTwin may later supply versioned policy evidence, but DecisionTrace must consume it through an agreed contract with tenant/identity semantics, provenance, fixture examples, and consumer tests. A direct read of RuleTwin tables is outside the design. DecisionTrace's standalone answer pipeline and evaluation can be built first. An integrated demo is complete only when the RuleTwin contract and both sides' tests pass. The portfolio [completion plan](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/05_DECISIONTRACE_COMPLETION_PLAN.md) and [release evidence matrix](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/04_RELEASE_EVIDENCE_MATRIX.md) track shared release claims.

## 8. How to run and verify the present demo

From the DecisionTrace repository root, install Python, Node/npm, and Docker Compose, then run:

~~~powershell
python tools/demo_preflight.py
~~~

This runs static/corpus/contract/web checks, starts or upgrades the local Compose stack, seeds fictional evidence, exercises the live suites, runs the candidate timing diagnostic and same-server restore smoke, and leaves the demo running. Open http://127.0.0.1:5174/ and use the [manual guide](demo-test-guide.md). To inspect only the static checks, run python tools/check_all.py. To inspect index drift without changing data, run the following inside the running stack:

~~~powershell
docker compose --env-file .env.example exec -T api python -m tools.rebuild_index
~~~

The optional --apply repairs detected drift. Stop services while retaining the database with docker compose --env-file .env.example down. Back up an existing persistent database before a major image or migration upgrade. The 2026-11-19 local upgrade did so and passed preflight; its local backup is intentionally excluded from Git. The [current main CI](https://github.com/Preethamreddy29/decisiontrace/actions/runs/44443407605) independently checks the fresh synthetic stack, while the local upgrade exercised an existing volume. Neither is a clean-host v1 disaster-recovery proof.

## 9. Source map

- [README](../../README.md), [progress log](../progress.md), [phase plan](../implementation-plan.md), and [requirements traceability](../requirements-traceability.md) give the quick status and dated history.
- [API routes](../../api/app/main.py), [query resolver](../../api/app/query.py), [exact citation gate](../../api/app/verification.py), [source and decision workflow](../../api/app/workflow.py), [retrieval](../../api/app/retrieval.py), [indexing](../../api/app/indexing.py), [watches](../../api/app/change_watch.py), [worker](../../api/app/worker.py), and [migrations](../../api/migrations) are the runtime source of truth.
- [OpenAPI](../../contracts/openapi.json), [event schema](../../contracts/events.schema.json), [architecture notes](../architecture/data-model.md), [temporal semantics](../architecture/temporal-model.md), and [ADRs](../decisions) define the design and contract intent.
- [Corpus manifest](../../corpus/manifest.json), [seed questions](../../corpus/gold.json), [draft holdout](../../corpus/holdout_v05_draft.json), [CI workflow](../../.github/workflows/ci.yml), and [demo preflight](../../tools/demo_preflight.py) anchor verification.
