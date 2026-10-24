# Governed Demo v0.3

**State:** locally implemented and verified on 2026-10-24. The full Phase 3 product gate remains open.

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
