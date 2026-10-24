# DecisionTrace Phase 0 Charter

**Status:** draft, 2026-10-23. This is a product hypothesis, not user-research evidence.

## Problem and users

Product decisions are spread across changing documents, tickets, tests, and releases. A reader may find the latest text but miss which decision was valid at a historical date, when the organization learned of a correction, or whether an implementation still matches the approved decision. An unsupported or unauthorized answer could mislead a release decision.

The initial roles are product owner (decision owner), engineer (implementation evidence), QA lead (test evidence), auditor (historical reconstruction), and executive viewer (limited summary). These are design personas; none has been interviewed for this project.

## First critical workflow

1. Ingest a versioned, permission-scoped synthetic source with checksum and provenance.
2. Have a human review and approve a structured decision contract.
3. Ask what was valid on a date and, separately, what was known as of a date.
4. Show each answer claim beside an exact source/version citation and relevant timeline.
5. Report conflict or abstain when approved, permitted evidence cannot support the answer.

The signature example is a fictional manual-override rule: an original decision is later corrected in the record, then superseded by a new approved policy. The UI must show these as different events rather than collapsing them into a single latest answer.

## First-demo acceptance

- A fresh local setup loads a fixed, versioned synthetic corpus and runs without manual database edits.
- A historical query and a current query produce the expected distinct answers.
- Every displayed factual claim opens its supporting source/version and is permission-checked.
- A missing-evidence query abstains; an unresolved contradiction is visibly flagged.
- The same corpus/version/query tuple reproduces the same structured result under the pinned deterministic portion of the pipeline.
- The scripted demo and automated checks pass on the same revision.

## Non-goals for the first demo

No live enterprise connectors, autonomous approval, unreviewed extracted decisions as truth, production customer data, cross-product database reads, or claims of enterprise security/scale. Natural-language generation may be added only after deterministic citation and temporal checks work; a structured answer is acceptable first.

## Measures and falsifiable assumptions

The gold set will track temporal accuracy, citation validity, supported-claim rate, abstention accuracy, permission denial, retrieval recall, latency, and memory. Initial numeric release thresholds come from the portfolio DecisionTrace runbook and remain unmeasured.

| Hypothesis | How it can fail |
|---|---|
| Reviewers need valid-time and recorded-time answers separately | Scripted tasks show no meaningful difference in decisions made with either answer. |
| Versioned citations are useful enough to justify review effort | Reviewers cannot verify an answer faster or more accurately than reading source history directly. |
| Human-approved decision contracts reduce false authority | Review still admits unsupported or contradictory contracts in controlled cases. |
| A local pipeline can meet useful latency on named hardware | Timed corpus evaluation exceeds an agreed interactive threshold. |

## Dependency decision

The portfolio originally sequenced DecisionTrace after RuleTwin v1. The maintainer requested parallel development on 2026-10-23. DecisionTrace may build and demo independently with synthetic evidence now. RuleTwin connection remains gated on a stable, versioned contract, examples, permission semantics, and passing consumer tests.
