# DecisionTrace

DecisionTrace is a local demo for reconstructing why a product decision was made, what applied on a chosen date, and which exact versioned evidence supports the answer. The supplied scenarios and data are fictional.

## Current status

The interactive v0.6 demo supports source intake, corrections, independent decision approval, historical questions with exact citations, downstream change review, and source revocation. Its answer resolver is deliberately bounded to the fictional manual-override and invoice-hold scenarios. It is not a general question-answering or production release.

The local foundation also has a validated outbox, concurrent read/revocation ordering, authorized PostgreSQL full-text chunk search, a dry-run-first chunk-index rebuild, and a same-server backup/restore smoke. These are [Stage A and B increments](docs/progress.md); the demo answer path still reads authorized source versions directly. The [portfolio completion plan](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/portfolio-ruletwin-sync/docs/05_DECISIONTRACE_COMPLETION_PLAN.md) tracks the full v1 gates.

Open work includes vector and model retrieval, hybrid answers with a claim verifier, broader ingestion and extraction review, semantic drift, a reviewed 100+ question evaluation, complete security and release drills, and RuleTwin integration. The 20 draft answer labels need independent human review. The optional OIDC token verifier has only synthetic issuer checks; a real provider and browser sign-in flow remain untested.

## Run the fictional demo

Install Python, Node/npm, and Docker Compose, then run this from the repository root:

```powershell
python tools/demo_preflight.py
```

The preflight builds the web app and local containers, seeds the fictional corpus, runs static and live checks, exercises a same-server restore, and leaves the demo running. Open [http://127.0.0.1:5174/](http://127.0.0.1:5174/). Sign in as **Cedar author / auditor** with the local passphrase `local-demo-only`. Follow the [demo test guide](docs/release/demo-test-guide.md) to compare historical answers, upload the [fictional invoice-hold file](corpus/demo-invoice-holds.md), obtain independent approval, inspect an exact citation, review a downstream change, and revoke its source.

The API readiness endpoint is [http://127.0.0.1:8001/health/ready](http://127.0.0.1:8001/health/ready). To stop the stack while keeping local data, run `docker compose --env-file .env.example down`. The demo binds services to loopback and uses published fictional credentials; do not load real customer or confidential data.

For static checks alone, run `python tools/check_all.py`. The [latest verified code CI run](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40436054619) covers the full live suite, index rebuild, and restore smoke. CI evidence is for the synthetic local stack; it does not close the v1 release gates.

## What is implemented

- Versioned, checksum-checked fictional sources with tenant, role, valid-time, and recorded-time controls; Markdown, transcript, and JSON sections have stable IDs and exact offsets.
- Governed source and decision workflows: text/file intake, allowlisted push snapshots, correction history, independent approval, idempotent protected mutations, audit/outbox records, and author-controlled source revocation.
- Bounded structured answers with exact authorized citations, conflict and abstention states, and a source drill-down. A later correction changes current evidence while earlier recorded-time queries can inspect the historical version unless it was revoked.
- Reviewed downstream watches for `tests`, `implements`, and `measures` relations. Reviewers classify a source-version change as drift or alignment; automatic semantic drift detection remains open.
- Internal full-text search over authorized temporal chunks, a safe index repair command, and local outbox/recovery checks. Search candidates are not yet used to generate demo answers.

## Project records

- [Progress and open work](docs/progress.md) · [Implementation plan](docs/implementation-plan.md) · [Requirements traceability](docs/requirements-traceability.md)
- [Stage A outbox and revocation ordering](docs/release/v07-outbox-stability.md) · [Full-text foundation](docs/release/v08-full-text-foundation.md) · [Restore smoke](docs/release/v09-restore-smoke.md) · [Index rebuild](docs/release/v10-index-rebuild.md)
- [v0.6 demo workflow](docs/release/v06-change-watch-revocation.md) · [Independent label review packet](docs/release/v05-review-packet.md) · [Design decisions](docs/decisions/ADR-001-postgresql-full-text-and-pgvector.md)

The project is [MIT licensed](LICENSE). DecisionTrace owns its database. Future RuleTwin integration will use a versioned contract and consumer tests.
