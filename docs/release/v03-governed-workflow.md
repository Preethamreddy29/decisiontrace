# Governed Demo v0.3

**State:** locally implemented and verified on 2026-10-24. [GitHub CI passed](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40113083114). The full Phase 3 product gate remains open.

## Demo path

At `http://127.0.0.1:5174`, sign in as **Cedar author / auditor** with the published local passphrase. Add the prefilled fictional text source, save a corrected version, then create a decision draft bound to the current source version. Attempting to approve it as the author fails. Switch to **Cedar independent reviewer**, approve the draft, ask the prefilled follow-up question, and open the exact cited passage. The source panel retains both versions; the decision panel shows the draft and reviewed state.

## Implemented boundary

- `POST/GET /v1/sources` and `POST/GET /v1/sources/{source_id}/versions` handle local text intake and source history. Source IDs and recorded timestamps are server-assigned; versions have content checksums, origin, valid interval, tenant and role permissions, and immutable text. A corrected version supersedes the prior version at its recorded time.
- `POST/GET /v1/decision-contracts`, review, and history create immutable draft/review versions. The author comes from the server session; an independent auditor must approve or reject. `If-Match` blocks stale review/version requests. Approval rechecks the bound evidence's tenant, role, checksum, current version, and valid interval.
- Approved manual-override decisions can supply answers with an exact sentence citation and decision-version ID. Drafts cannot. A later correction does not silently retarget approval to new evidence; current queries abstain until reviewed again, while earlier recorded-time queries retain the historical answer.
- Protected mutations use idempotency keys and write audit/outbox records in the same transaction. The worker acknowledges these local demo events without an external delivery target.

## Verification

`python tools/check_all.py`, formal OpenAPI validation, the database/worker smoke, the original 25-case preview, the 14 v0.2 paraphrases, and live response-schema validation pass. `python -m tools.eval_v03` inside the API container checks malformed input, duplicate mutations, source corrections, stale ETags, author/reviewer separation, approval and rejection, historical query cutoffs, stale evidence abstention, cross-tenant/role denial, exact source opening, and audit/outbox pairing. Browser review completed the same author-to-reviewer-to-answer flow.

## Remaining limits

Intake is bounded text through a form, not file/connector ingestion or structure-aware chunking. The decision statement is entered by a person; there is no extraction model. The resolver supports a bounded fictional manual-override domain. Credentials are shared synthetic demo credentials, not production identity. Independent human-reviewed answer evaluation, 100+ gold cases, deletion/retention, full failure and threat suites, general retrieval, and RuleTwin integration remain open.

## Next steps

1. **v0.4 — evaluation-ready evidence.** Add structure-aware source sections with stable IDs and exact passage retrieval, then broaden the fictional corpus beyond the current manual-override examples. Preserve version, recorded-time, permission, and citation behavior through corrections. The gate is a clean-start demo and checks that every returned citation resolves to the exact authorized source version and section.
2. **v0.5 — Phase 3 product gate.** Replace shared demo identities with production-capable authentication and tenant authorization. Freeze an independently reviewed answer holdout covering current and historical questions, corrected sources, permission denial, unsupported questions, and answerable cases. Publish reproducible citation, temporal, permission, and abstention results with failure examples. Close the gate only when the identity, ingestion, and evaluation evidence is recorded; seed prompts and paraphrases remain regression checks.
3. **Phases 4–6 — v1 breadth and hardening.** Expand source types and two-tenant behavior, reach the planned 100+ reviewed gold questions, and implement drift, source retention/deletion, audit and outbox delivery/replay, recovery, and the remaining failure and threat tests. Record the permission, citation, temporal, abstention, and injection gates on versioned fixtures.
4. **RuleTwin connection.** Agree on a versioned evidence contract, sample fixtures, tenant/authentication semantics, and consumer contract tests with RuleTwin. Integrate through that interface after both sides pass the contract tests; keep the standalone DecisionTrace demo runnable.

The immediate next build is **v0.4**. The phase status and open gaps remain tracked in [the implementation plan](../implementation-plan.md) and [progress log](../progress.md).
