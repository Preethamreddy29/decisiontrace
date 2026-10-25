# v0.5 identity, intake, and evaluation preview

**Date:** 2026-10-25
**Status:** Local demo implementation complete; Phase 3 product gate open.

## Delivered

- Optional `AUTH_MODE=oidc` verifies externally issued RS256 access tokens against a configured HTTPS JWKS, issuer, audience, expiry, subject, tenant allowlist, and role claim. It rejects unsupported algorithms and missing or conflicting signing keys. `/v1/session` reports the verified identity. Demo credentials and `/demo/login` are disabled in OIDC mode.
- The local UI can accept an externally obtained bearer token in OIDC mode. The token stays in page memory. The UI does not initiate an OAuth authorization-code flow or manage token refresh.
- Authors can upload UTF-8 Markdown, transcript text, or JSON through the UI or raw upload API. Intake checks the filename, kind, media type, 32 KiB byte limit, 10,000-character source limit, source schema, role, and tenant.
- An allowlisted push connector endpoint accepts checksum-verified snapshots with remote object and revision IDs. It creates or versions a tenant-scoped source, rejects conflicting or replayed remote revisions, and records the connector provenance.
- Source versions persist deterministic section chunks with offsets and SHA-256 hashes. The chunk size is capped at 1,200 characters, and unchanged sections retain their chunk IDs across unrelated edits. The bounded answer resolver still reads authorized full source text; chunk-based retrieval is later work.
- A 20-case draft evaluation set covers historical cutoffs, correction, supersession, tenant denial, conflict, abstention, and citation integrity. The diagnostic runner reports status, required labels and phrases, and exact authorized source spans.

## How to run the demo

Start and seed the stack as in the README. Sign in with the published fictional Cedar auditor account and `local-demo-only`, then use **Upload a source file** in **Take new evidence through review**. A Markdown file such as `fictional-policy.md` can contain:

```markdown
# Cedar payment controls
## Invoice holds
Invoice holds require finance approval before release.
## Scope
This fictional policy applies to Cedar invoices.
```

Select `2026-07-01` and upload. The saved source and its sections appear in the workflow. Draft a decision from that source, switch to the independent Cedar reviewer, approve it, and ask who approves Cedar invoice holds. The answer links to the exact cited passage. The existing historical manual-override examples remain available.

For connector demonstrations, set `CONNECTOR_IDS=fictional-push`; an authorized auditor can `POST /v1/connectors/fictional-push/snapshots` using the versioned OpenAPI contract. The route is an authenticated push boundary, not a live pull from an external service.

For external identity, configure `AUTH_MODE=oidc`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`, and `OIDC_ALLOWED_TENANTS` for a trusted issuer that signs `tenant` and `role` claims. Deployment must provide HTTPS, issuer provisioning, lifecycle management, and an actual token-acquisition flow.

## Verification and gate

`python tools/check_all.py` passes. After a rebuilt local stack and seed, `python -m api.app.smoke`, `python -m tools.eval_demo` (25 seed questions), `python -m tools.eval_v02` (14 paraphrases), and `python -m tools.eval_v03`, `eval_v04`, and `eval_v05` all pass. `python -m tools.eval_holdout_v05` reports 20/20 statuses, 20/20 required labels and phrases, and 20/20 exact authorized citation spans. Its labels remain `agent-authored-draft-awaiting-independent-human-review`, so that result is diagnostic. GitHub Actions reruns these checks and formal contract validation on the pushed commit.

The independent label review described in [v0.5 review packet](v05-review-packet.md) and integration with a real identity provider remain open. The 20-case set is not a general question-answering accuracy claim. RuleTwin integration still depends on its stable evidence contract and consumer tests.
