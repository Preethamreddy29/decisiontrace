# Structured Evidence Demo v0.4

**State:** locally implemented and verified on 2026-10-25. The full Phase 3 product gate remains open.

## Demo path

At `http://127.0.0.1:5174`, sign in as **Cedar author / auditor** with the published local passphrase. Select **Use invoice-hold example**, add its fictional Markdown source, and create a decision draft. Switch to **Cedar independent reviewer**, approve the draft, ask the prepared question, and open the citation. The opened panel shows the **Invoice holds** section and highlights the exact quoted sentence. The source history also lists the parsed section titles.

## Implemented boundary

- Markdown headings, transcript speaker turns, and JSON leaf paths produce deterministic section IDs and exact character spans. Section IDs are based on structure; edits to an unrelated section leave the other IDs unchanged. Existing seed source kinds remain a single `body` section.
- Authorized source-version responses now include section metadata. Query citations carry the section ID containing their exact quote. Replayed query answers recheck both the quote and its section against currently visible evidence.
- A second bounded topic, fictional Cedar invoice holds, follows the existing source-version, independent-review, temporal, and permission rules. Unapproved or corrected evidence cannot become a current approved answer without review.
- The web demo offers a prepared invoice-hold source and shows the cited section rather than the entire document.

## Verification

`python tools/check_all.py` passed, including the web build and structural contract checks. The database/worker smoke, 25 seed cases, 14 v0.2 paraphrases, v0.3 workflow, and new `python -m tools.eval_v04` live check passed. The new check covers stable Markdown section IDs, transcript and JSON paths, independent approval for the second topic, exact citation offsets, tenant isolation, corrected-source abstention, and historical answers. Browser review completed the same source-to-review-to-section flow.

## Remaining limits

This is deterministic section parsing and bounded question resolution, not general retrieval or model extraction. Source text still enters through a form; file/connector intake and bounded chunk indexing remain open. JSON values and transcript turns are sectioned but are not yet answer topics. The independent answer holdout, production identity, retention/deletion, broader threat/failure gates, and RuleTwin interface remain pending. See the [implementation plan](../implementation-plan.md) for the next gate.
