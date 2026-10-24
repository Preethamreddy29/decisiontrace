# DecisionTrace

DecisionTrace is a local-first product for reconstructing *why* a product decision was made, what applied at a particular time, and which versioned evidence supports the answer. All initial scenarios and data are fictional.

## Current status

Phase 0's synthetic corpus gate, the Phase 1 design gate, and the Phase 2 local foundation gate are complete. The interactive v0.2 synthetic demo accepts new decision questions, separates valid time from recorded time, and opens exact cited source passages. The full Phase 3 product gate, production identity, general question answering, model, and RuleTwin integration remain open. The separate RuleTwin project is being developed in parallel.

The demo uses a deterministic, bounded resolver over the frozen fictional corpus. It distinguishes correction from supersession, flags draft/test conflicts, and abstains outside supported manual-override questions. The original 25 seed prompts and 14 separate v0.2 paraphrases are reproducibility checks, not an independent human-reviewed holdout. RuleTwin integration follows a stable, versioned evidence contract and a consumer test.

Start with the [charter](docs/product/charter.md), [corpus plan](docs/product/synthetic-corpus.md), [temporal model](docs/architecture/temporal-model.md), [implementation plan](docs/implementation-plan.md), and [progress log](docs/progress.md).

Run `python tools/validate_corpus.py` to verify the 14 synthetic source versions, 25 labeled seed cases, 14 v0.2 paraphrases, and manifest. The corpus and project are MIT licensed; see [LICENSE](LICENSE).

## Local foundation

From this repository, run `docker compose --env-file .env.example up --build -d`. Load the fictional corpus with `docker compose --env-file .env.example exec -T api python -m api.app.seed`, then open `http://127.0.0.1:5174`. Sign in as a fictional demo identity with passphrase `local-demo-only`. Try **Known on 10 May**, **Corrected record**, and **After supersession**, then open a citation. The API readiness endpoint is `http://127.0.0.1:8001/health/ready`. Run `docker compose --env-file .env.example exec -T api python -m api.app.smoke`, `docker compose --env-file .env.example exec -T api python -m tools.eval_demo`, and `docker compose --env-file .env.example exec -T api python -m tools.eval_v02` for local checks. Stop the stack with `docker compose --env-file .env.example down`; omit `-v` to retain local data. These commands are for a loopback-only synthetic demo environment.

Run `python tools/check_all.py` for corpus, contract, credential-pattern, web-build, and Compose-configuration checks. The [v0.2 demo record](docs/release/v02-interactive-demo.md) lists the current proof and limits; earlier [foundation](docs/release/phase2-foundation-gate.md) and [curated preview](docs/release/phase3-demo-preview.md) records remain available.

## Boundaries

- No real customer, employer, or confidential product data.
- No answer is authoritative until source permission, temporal scope, and citation support are checked.
- Extracted decisions require human review before becoming approved decision contracts.
- DecisionTrace owns its own data. Future RuleTwin integration uses a versioned interface, never direct database access.
- The initial target is a local demo. Production or evaluation claims require reproducible evidence.
- The shared demo passphrase and server-issued bearer tokens are for fictional loopback use only. Tokens expire after eight hours and become invalid when the API restarts.
