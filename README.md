# DecisionTrace

DecisionTrace is a local-first product for reconstructing *why* a product decision was made, what applied at a particular time, and which versioned evidence supports the answer. All initial scenarios and data are fictional.

## Current status

Phase 0's synthetic corpus gate, the Phase 1 design gate, and the Phase 2 local foundation gate are complete. The interactive v0.5 synthetic demo adds file upload, a checksum-verified push connector, persisted section chunks, and optional external OIDC token verification to the v0.4 source-version and independent-review workflow. The full Phase 3 product gate remains open until the new answer labels receive independent human review and an actual identity provider is exercised. General question answering, a model, and RuleTwin integration remain open. The separate RuleTwin project is being developed in parallel.

The demo uses a deterministic, bounded resolver over the frozen fictional corpus and locally authored demo evidence. An approved decision binds exact source-version IDs; a later correction makes stale evidence unavailable to current answers while preserving historical answers. It distinguishes correction from supersession, flags draft/test conflicts, and abstains outside supported manual-override and invoice-hold questions. Markdown headings, transcript turns, and JSON paths receive deterministic section IDs; answer citations resolve to exact authorized sections. Persisted bounded chunks support later retrieval work; the current resolver still reads authorized full source text. The original 25 seed prompts, 14 v0.2 paraphrases, v0.3–v0.5 workflow checks, and agent-authored 20-case draft are reproducibility checks, not an independent human-reviewed accuracy claim. RuleTwin integration follows a stable, versioned evidence contract and a consumer test.

Start with the [charter](docs/product/charter.md), [corpus plan](docs/product/synthetic-corpus.md), [temporal model](docs/architecture/temporal-model.md), [implementation plan](docs/implementation-plan.md), and [progress log](docs/progress.md).

Run `python tools/validate_corpus.py` to verify the 14 synthetic source versions, 25 labeled seed cases, 14 v0.2 paraphrases, and manifest. The corpus and project are MIT licensed; see [LICENSE](LICENSE).

## Local foundation

From this repository, run `docker compose --env-file .env.example up --build -d`. Load the fictional corpus with `docker compose --env-file .env.example exec -T api python -m api.app.seed`, then open `http://127.0.0.1:5174`. Sign in as **Cedar author / auditor** with passphrase `local-demo-only`. Under **Take new evidence through review**, choose **Use invoice-hold example**, add the fictional source, and create a decision draft. Switch to **Cedar independent reviewer** with the same local passphrase and approve it. The page sets the question and dates for the approved answer; open the exact cited section. The earlier historical examples remain available. The API readiness endpoint is `http://127.0.0.1:8001/health/ready`. Run `python tools/check_all.py` and the API-container commands `python -m api.app.smoke`, `python -m tools.eval_demo`, `python -m tools.eval_v02`, `python -m tools.eval_v03`, and `python -m tools.eval_v04` for local checks. Stop the stack with `docker compose --env-file .env.example down`; omit `-v` to retain local data. These commands are for a loopback-only synthetic demo environment.

Run `python tools/check_all.py` for corpus, contract, credential-pattern, web-build, and Compose-configuration checks. The [v0.5 release record](docs/release/v05-identity-intake-evaluation.md) lists the current proof and limits, and the [review packet](docs/release/v05-review-packet.md) explains the independent label gate. Earlier [v0.4](docs/release/v04-structured-evidence.md), [v0.3](docs/release/v03-governed-workflow.md), [v0.2](docs/release/v02-interactive-demo.md), [foundation](docs/release/phase2-foundation-gate.md), and [curated preview](docs/release/phase3-demo-preview.md) records remain available.

For the v0.5 intake demo, sign in as the Cedar auditor and use **Upload a UTF-8 file** under **Take new evidence through review**. Markdown, transcript text, and JSON files are accepted up to 32 KiB; then draft and independently approve a decision using that source. In the API container, `python -m tools.eval_v05` checks identity and intake boundaries, while `python -m tools.eval_holdout_v05` reports the 20-case draft diagnostic. Set `CONNECTOR_IDS=fictional-push` for the authenticated snapshot endpoint. See the v0.5 release record for the external OIDC configuration and limits.

## Boundaries

- No real customer, employer, or confidential product data.
- No answer is authoritative until source permission, temporal scope, and citation support are checked.
- Extracted decisions require human review before becoming approved decision contracts.
- DecisionTrace owns its own data. Future RuleTwin integration uses a versioned interface, never direct database access.
- The initial target is a local demo. Production or evaluation claims require reproducible evidence.
- The shared demo passphrase and server-issued bearer tokens are for fictional loopback use only. Tokens expire after eight hours and become invalid when the API restarts. `AUTH_MODE=oidc` is a separate strict API verification mode; deployment still needs a trusted issuer, HTTPS, token acquisition, and lifecycle operations.
