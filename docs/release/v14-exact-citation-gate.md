# Exact citation gate for bounded answers

**Date:** 2026-11-20
**Scope:** Stage C exact-evidence verification for the fictional v0.6 answer path.

The public query route now verifies a newly resolved answer before storing or returning it, and verifies a stored answer again on an idempotent retry. An invalid new answer becomes an abstention without displayed claims; an invalid cached answer is refused with HTTP 409. The answer records verification profile "exact-authorized-quote-v1".

The gate reselects source versions under the verified actor's tenant and role, the recorded cutoff, optional source scope, supersession, and revocation rules. It checks the selected valid date, source and version IDs, source label, exact quote and character offsets, and containing section ID. A displayed claim must equal its one cited quote. Authored Markdown, transcript, and JSON answers require an approved decision version. When a claim names a decision version, the gate checks that decision's tenant, approval, effective interval, recorded cutoff, evidence binding, and visibility of every bound evidence version. The tenant evidence lock held by the query keeps revocation from committing between verification and return.

The "tools.eval_v14_verifier" check tests a valid historical answer, other-tenant denial, invented source/version/decision IDs, revoked and future-recorded evidence, invalid effective date, altered section/offset/label, unsupported claim text, missing citation, new-answer abstention, and refusal of a tampered stored answer. The 2026-11-20 full local preflight passed all prior gates, this new gate, the candidate timing diagnostic, and same-server restore.

This is a deterministic **exact-quotation and authorization** check for the bounded resolver. It does not establish that an arbitrary generated paraphrase is entailed by its source or relevant to the user's question. Semantic retrieval, reranking, structured generation, broader claim-support evaluation, independent answer labels, and a real OIDC provider remain open. The 20-case draft holdout is still diagnostic.
