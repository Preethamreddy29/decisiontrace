# Progress

**As of:** 2026-10-25
**Milestone:** Phase 0 complete; Phase 1 design gate passed; Phase 2 local foundation gate passed; v0.5 identity/intake preview in verification; full Phase 3 product gate open

## 2026-10-25 v0.5 identity, intake, and evaluation preview

- Added an optional OIDC mode that verifies RS256 access tokens against HTTPS JWKS, issuer, audience, expiry, signed tenant and role claims. Demo login is disabled in this mode. A real identity provider has not yet been exercised.
- Added bounded UTF-8 file upload and allowlisted, checksum-verified push-connector snapshots with tenant-scoped remote revision tracking. New source versions persist deterministic section chunks with offsets and hashes; query retrieval still scans authorized full source versions.
- Added a 20-question draft evaluation set and a runner that checks status, expected labels and phrases, and exact authorized citation spans. It currently reports 20/20 on those measures, but the labels were authored by the implementation agent. The maintainer has offered to review them independently. See `docs/release/v05-review-packet.md` and `docs/release/v05-identity-intake-evaluation.md`.

## 2026-10-25 structured v0.4 evidence

- Added deterministic Markdown heading, transcript turn, and JSON leaf sections with exact source offsets and stable structural IDs. Authorized source responses expose section metadata; citations point to the containing section.
- Added a second bounded reviewed topic for fictional invoice holds. The demo provides a prepared source and shows the highlighted exact section after independent approval.
- Static checks and live smoke, original 25 seed cases, 14 v0.2 paraphrases, v0.3 workflow, and v0.4 structure/citation checks passed. Browser review completed the invoice-hold approval and citation flow. See `docs/release/v04-structured-evidence.md`.

## 2026-10-24 governed v0.3 workflow

- Added a third checksummed migration for authored source origin/lineage, decision title/supersession reference, and mutation idempotency. Source text intake records checksum, tenant, permission scope, origin, valid and recorded time; corrected versions preserve the earlier source and its history.
- Added server-derived authorship and independent auditor review. Draft, approval, and rejection are immutable decision versions; stale ETags, self approval, cross-tenant access, and superseded evidence are rejected. Protected mutations write audit and local outbox events in the same transaction.
- Approved decisions can supply an exact source-sentence answer. Drafts do not become authority. A later source correction makes the approved decision's old evidence unavailable to a current query, while a query at the earlier recorded cutoff can still inspect it.
- The UI now provides source creation/correction, source history, decision draft/review, identity switching, and an approved answer with the exact source passage. Browser review completed the author-to-reviewer-to-answer flow and confirmed self approval is blocked.
- The live v0.3 check covers versioning, idempotency, review separation, historical answers, stale evidence, tenant/role controls, and audit/outbox pairing. Existing 25 seed prompts and 14 v0.2 paraphrases still pass. See `docs/release/v03-governed-workflow.md` for scope and limits.

## 2026-10-24 interactive v0.2

- Added a server-verified synthetic demo login with three identities. Tenant and role now come from a signed bearer token, not query fields. The API signing key is random per startup; the shared published passphrase remains local-demo-only.
- Implemented structured `/v1/query` over stored source versions with temporal and permission filtering, exact sentence citations, retry-safe idempotency, and reauthorized source drill-down. The previous unauthenticated `/demo/query` HTTP route was removed.
- Replaced the curated-only page with an interactive question box, valid/recorded time controls, identity switch, example prompts, conflict/abstention states, and clickable highlighted source passages.
- Added a second checksummed migration, labeled seed sources, and a 14-case paraphrase set frozen in the corpus manifest. The live v0.2 evaluation passes those questions plus token, tenant, time, quote-offset, source-detail, and idempotency checks. Live Answer and SourceVersion responses validate against OpenAPI.
- Browser review showed the 10 May one-reviewer answer, its opened source, and the corrected two-reviewer answer. See `docs/release/v02-interactive-demo.md` for exact scope and limitations.

## Earlier 2026-10-24 foundation and preview record

- Added a clearly labeled synthetic `/demo/query` route backed by tenant/role-filtered stored source versions and a curated deterministic answer resolver. The UI can compare the then-known 10 May record, its later correction, and the policy effective after 20 May, with expandable source versions.
- Evaluated all 25 seed prompts for expected status and required citation IDs, with critical answer-phrase checks, historical no-future-citation check, and unsupported-question abstention. The clean GitHub Actions run also passed. This is a seed-set preview, not an independent holdout or general question-answering score. See `docs/release/phase3-demo-preview.md`.
- Chose the MIT license after the maintainer delegated the suitable-license choice.
- Authored 14 versioned synthetic source records and 25 exact gold labels, including valid/recorded-time distinction, correction, supersession, drift, conflict, abstention, permission denial, revocation, and adversarial text.
- Froze corpus file hashes in `corpus/manifest.json`. `python tools/validate_corpus.py` passes. Corrected an early source that inadvertently mentioned a future correction in a historical version.
- Added the conceptual ERD/lifecycle and temporal rules, 10 ADRs, requirements traceability, threat-to-test map, signature UI-to-data trace, versioned OpenAPI and event schemas.
- Validated 13 OpenAPI 3.1 operations with `openapi-spec-validator==0.7.2`, checked the event schema with Draft 2020-12, and passed `python tools/validate_contracts.py`. Phase 1's **design** gate is recorded in `docs/release/phase1-design-gate.md`; no runtime control is implied by it.
- Built a Phase 2 Compose stack with PostgreSQL, one checksummed baseline migration, FastAPI readiness service, lease-based worker skeleton, and React readiness shell. API and web containers run as non-root users.
- `npm run build` and `python tools/check_all.py` pass. `docker compose --env-file .env.example up --build -d` starts the local stack; API and PostgreSQL report healthy; the web page and its API proxy return HTTP 200.
- Seeded the fictional corpus twice without duplicates. `python -m api.app.smoke` in the API container passes with 2 tenants, 14 source versions, 1 migration, and a worker-delivered outbox ping.
- Verified an unknown API route returns a problem JSON 404 with a request ID. Stopping PostgreSQL made readiness return problem JSON 503; restarting it restored HTTP 200.
- Committed and pushed the foundation at `b52ffaf`. Its clean GitHub Actions run passed all foundation steps; see `docs/release/phase2-foundation-gate.md`.

## Current open work

- Phase 2's foundation gate is closed. The local secret-pattern scanner is a narrow tripwire, not a complete supply-chain audit.
- `/v1/query`, governed text/file/connector-push source versions, decision review/history, exact source GET, and a stored chunk index are implemented for the bounded synthetic demo. General chunk retrieval, external pull connectors, deletion, drift/evaluation operations, and other planned API operations remain open.
- An external-token verifier exists but has not been integrated with a real issuer or complete browser sign-in flow. No model, independent human-reviewed holdout, 100-question set, full security/failure suite, or RuleTwin connector exists. The local demo credentials are deliberately shared and unsuitable for deployment.
- The remaining Phase 3 product work is independent review of answer labels and a real identity-provider integration test. Broader product behavior and security depth continue in later phases.

## Next checkpoint

Complete the independent label review, exercise the external identity configuration with a real issuer, and then decide whether the Phase 3 product gate is met. Integration with RuleTwin remains gated on its stable evidence contract and consumer tests.

## Original 2026-10-23 setup record

## Done

- Confirmed the supplied local folder and GitHub repository were empty at project start.
- Initialized the local Git repository on `main`.
- Defined the product boundary, first-demo workflow, synthetic-only rule, and parallel RuleTwin dependency.
- Drafted the six-month corpus outline and 25 initial gold-question specifications.
- Drafted valid/recorded-time, correction/supersession, citation, and authorization invariants.
- Established milestone gates and an explicit list of Phase 0 gaps.

## Not done

- No synthetic source corpus, exact gold answers, corpus manifest, or license decision.
- No completed Phase 1 ERD, API/event contracts, ADRs, threat-to-test mapping, or reviewed security design.
- No application code, tests, database, UI, model, local demo, RuleTwin connection, CI, or release.
- Nothing has been committed or pushed to GitHub as part of this setup.

## Next checkpoint

Finish Phase 0 corpus and answer labels, then validate the Phase 1 contracts before implementing the standalone temporal cited-answer slice. Keep all claims of demo readiness tied to runnable checks and a clean-start script.
