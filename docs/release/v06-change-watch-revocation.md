# v0.6 preview: change watches and source revocation

**Date:** 2026-10-25  
**Scope:** local fictional DecisionTrace demo; Phase 4 increment, not the full Phase 4 exit gate.

## What is available

- An auditor can link the current approved decision version and one of its exact evidence versions to a downstream source with a typed `tests`, `implements`, or `measures` relation. The linked source version is the baseline.
- When that downstream source receives a new version, the watch becomes **needs review**. It displays the approved evidence, linked baseline, and current downstream text with immutable version IDs. A different auditor can record **drift** or **aligned** with a reason. A later source version creates a new review item. This detects a changed source version, not a semantic contradiction by itself.
- A source author can revoke an authored source with a reason and current ETag. Every version becomes unavailable to source listing, history, citation opening, decision-history visibility, and question answering. Indexed chunks and tenant answer caches are removed, and stored idempotent mutation responses are redacted. Connector revisions cannot restore a revoked binding. An audit and outbox record are written in the same transaction.
- The UI exposes watch creation, side-by-side source comparison, independent review, and source revocation.

## Verification

`python tools/demo_preflight.py` builds the web and containers, applies six checksummed migrations, seeds the fictional corpus, and runs the original 25 seed questions, 14 paraphrases, v0.3–v0.5 evaluations, the draft 20-case holdout diagnostic, file-to-review demo readiness, synthetic OIDC route test, and new v0.6 live checks. The v0.6 checks cover tenant boundaries, approved-only links, version-change detection, independent review, stale version rejection, revocation of all source versions, query cache and chunk removal, retry redaction, and audit/outbox pairing. The preflight leaves the demo at `http://127.0.0.1:5174/`.

## Limits and remaining gates

- Reviewers classify version changes manually. Automatic semantic contradiction detection, broader source adapters, an extraction review queue, and a decision-health dashboard remain Phase 4 work.
- Revocation is an API and retrieval withdrawal. Raw source rows remain in the local database for audit; physical deletion and retention policy remain open.
- The 20-case answer set is still draft until independent human label review. A real OIDC issuer integration, 100+ reviewed questions, external connector pulls, full security/failure drills, and a stable RuleTwin evidence contract remain open.
- The OpenAPI file is a partial implemented-slice contract. The older event schema remains a design contract and does not yet describe all local generic outbox payloads.

See [demo-test-guide.md](demo-test-guide.md) for manual scenarios.
