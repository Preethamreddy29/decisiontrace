# Interactive Demo v0.2

**State:** implemented and locally verified on 2026-10-24. The full Phase 3 product gate remains open.

## User flow

At `http://127.0.0.1:5174`, a user selects a fictional Cedar or Lumen demo identity, enters the shared local passphrase, asks a manual-override decision question, and chooses both the policy-valid date and the UTC recorded-time cutoff. The API derives tenant and role from a signed, expiring token. The page shows exact source-sentence claims and opens each cited version after a fresh authorization check. Example chips demonstrate the original transcript, later correction, superseding policy, drift, and abstention. The question box also accepts new paraphrases within this bounded domain.

## Implementation boundary

- `POST /v1/query` implements structured answers for the synthetic manual-override corpus. It filters source versions by tenant, role, recorded time, supersession, revocation, and optional source IDs before selecting evidence.
- `GET /v1/sources/{source_id}/versions/{version_id}` rechecks authorization and recorded time. Citations include the exact quote and character offsets, validated against stored content.
- An idempotency key returns the same stored answer on retry, rejects reuse with a different query, and refuses a stored answer if its cited evidence is no longer available.
- Demo tokens use a random server-side signing key and expire after eight hours. The published shared passphrase is useful only for this fictional loopback demo; it is not production authentication.
- Unsupported questions and dates without eligible evidence abstain. Cross-tenant questions are denied without disclosing source content.

## Local verification

- `python tools/check_all.py` passes corpus, contract, secret-pattern, web-build, and Compose checks.
- `docker compose --env-file .env.example up --build -d` starts the stack; the migration and seed leave two tenants, 14 labeled source versions, and two checksummed migrations. The worker smoke passes.
- `python -m tools.eval_v02` inside the API container passes 14 separately authored paraphrases covering historical/current answers, correction, supersession, drift, draft conflict, abstention, cross-tenant denial, and role filtering. It also verifies exact quote offsets, idempotency, token tampering, wrong passphrase, future-source denial, and source drill-down authorization.
- `python tools/verify_v02_contract.py` validates a live Answer and SourceVersion response against the updated OpenAPI schemas.
- Browser review confirmed the login form, historical one-reviewer answer, exact source opening, and corrected two-reviewer answer.

## Limits before a broader product claim

The resolver deliberately quotes source sentences and supports a bounded fictional policy domain. The 14 paraphrases were authored within this repository before the resolver code; they are distinct from the original 25 seed prompts but are not independent human review. Governed source ingestion, decision approval, production identity, general retrieval, deletion, complete threat suite, larger evaluation, and RuleTwin integration remain open. The other planned OpenAPI operations are not implemented by v0.2.
