# DecisionTrace demo test guide

**For:** the local fictional v0.6 demo. These steps use no real customer data. The sample file SHA-256 is `181b863fb5462c35de608e0fca195c39b1bebd0ae43e72ad95d423fbbae890f2`.

## Prepare once

1. In `D:\sunny\Profile\projects\decisiontrace`, run `python tools/demo_preflight.py`. It builds the app, preserves the local database, seeds the fictional corpus, runs static/live checks, and leaves the demo running. A passing run ends with `Demo preflight passed`.
2. Open `http://127.0.0.1:5174/`. The page should say **Local service Ready**.
3. Sign in as **Cedar author / auditor** with the published demo passphrase `local-demo-only`.

## Manual scenarios

| Test | Action | Expected result |
|---|---|---|
| Historical record | Select **Known on 10 May**, then **Ask DecisionTrace**. Open its cited source. | Answer says **one reviewer**; the cited passage is highlighted in the authorized source. |
| Later correction | Select **Corrected record** and ask. | Answer says **two independent reviewers**; the source version differs from the earlier record. |
| Supersession | Select **After supersession** and ask. | Answer says overrides are **disabled**. |
| Missing evidence | Select **Missing evidence** and ask. | Status is **abstain**, without a fabricated citation. |
| File to decision | Under **Take new evidence through review**, choose [demo-invoice-holds.md](../../corpus/demo-invoice-holds.md), leave format **Markdown** and valid date `2026-07-01`, then select **Upload file**. | The source appears with an upload origin and three sections. The suggested decision statement changes to invoice holds. |
| Independent review | Select **Create decision draft**. Try to approve it as the Cedar author, then use **Switch identity** and sign in as **Cedar independent reviewer**. Approve the draft. | Self approval is refused; the other auditor can approve. The decision history shows draft then approved. |
| Cited answer | Ask the prepared invoice-hold question after approval; open the citation. | Answer says **finance approval before release**. The approved decision version and highlighted **Invoice holds** section are visible. |
| Tenant boundary | Switch to **Lumen auditor**. | Cedar-authored sources and decisions are absent from Lumen's lists. A Cedar question returns denied. |
| Downstream change watch | Switch back to **Cedar author / auditor**. Add a new source with origin `Fictional invoice test` and text `# Invoice test\n## Assertion\nThe test requires finance approval before invoice release.` Select the approved invoice-hold decision and this source under **Watch downstream changes**, then create a **Tests** watch. Select the test source, change its text to `# Invoice test\n## Assertion\nThe test releases an invoice without finance approval.`, and choose **Save corrected version**. | The watch moves from **current** to **needs review**. Expanding it shows the approved policy, the linked test baseline, and the current test version. The status describes a source-version change; it does not automatically assert semantic drift. |
| Independent drift review | Switch to **Cedar independent reviewer**, expand the changed watch, and choose **Confirm drift**. Enter a reason of at least eight characters. | The watch becomes **drift** with the reviewer's reason. Its creator cannot review it. A later test-source correction creates a fresh **needs review** item. |
| Revocation | Switch to **Cedar author / auditor**, select that fictional test source, and choose **Revoke source**. Enter a reason. | All versions of that test source disappear from source history, answer evidence, and the watch view. The local audit event remains. Revocation cannot be undone from the UI. |

The example source becomes a real record in the local fictional database when you upload it. Use a fresh filename for repeated upload tests if you want to distinguish the results. The preflight checks clean up their own disposable sources; they do not remove your manual demo records. Revocation withdraws source evidence from the API and index; it retains the raw row for local audit and is not physical erasure.

## Results to send back

For any failed step, send the scenario name, what you clicked, the visible result or error, and a screenshot if possible. Record whether the answer and cited source agree at the selected valid and recorded times. The [v0.5 review packet](v05-review-packet.md) is the separate independent-label review you offered to complete; corrections or approval there are needed for the Phase 3 answer-quality gate.

The optional external identity mode needs your issuer URL, JWKS URL, audience, and signed tenant/role claim mapping before a real-provider test. The preflight script tests the API routes with a synthetic signed issuer but does not claim that external integration is complete.
