# Signature Workflow Trace — Design

**Status:** planned UI-to-data path, not an implemented flow.

| User step | Contract | Data and control | Required check |
|---|---|---|---|
| Upload fictional meeting record | `POST /v1/sources` with idempotency key | Authenticate, derive tenant, validate type/size/checksum, append `source_version` and outbox event | Duplicate request yields one logical version; wrong tenant cannot select scope. |
| Review extracted decision | `POST /v1/decision-contracts`, then `/review` with `If-Match` | Candidate stays draft; independent approver binds exact evidence-version IDs | Draft cannot answer as approved; stale/self approval fails. |
| Ask 10 May valid-time question | `POST /v1/query` with `valid_on=2026-05-10` and current recorded cutoff | Permission filter, valid-time filter, approved contract, corrected meeting version | Answer cites exact corrected source and policy version. |
| Ask what was known on 10 May | Same endpoint with `recorded_as_of=2026-05-10T23:59:59Z` | Retrieval cannot see 12 May correction or approved record | Answer shows the original one-reviewer transcript with correction caveat in later review. |
| Ask 20 May policy | Same endpoint with `valid_on=2026-05-20` | Half-open interval ends earlier decision; supersession link selects approved new decision | Overrides disabled; 19 May still resolves to prior policy. |
| Open a citation | `GET /v1/sources/{source_id}/versions/{version_id}` | Recheck current permission and revocation; do not trust answer's earlier permission | Revoked or cross-tenant source cannot open. |
| Inspect stale test | Decision history plus later drift scan contract | Compare approved policy to active test expectation; link both versions | Finding is reviewable evidence, not an automatic code change. |

The first standalone demo may use a deterministic structured-answer mode. Natural-language generation is optional and cannot bypass the permission, temporal, and citation checks. RuleTwin evidence enters through a future versioned adapter after contract tests pass; no direct RuleTwin database query belongs in this path.
