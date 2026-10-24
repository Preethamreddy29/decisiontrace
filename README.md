# DecisionTrace

DecisionTrace is a local-first product for reconstructing *why* a product decision was made, what applied at a particular time, and which versioned evidence supports the answer. All initial scenarios and data are fictional.

## Current status

Phase 0's synthetic corpus gate and the Phase 1 design gate are complete. Phase 2 local engineering foundation is in progress: the API, database, worker, and readiness web shell now start locally. The historical answer workflow, model, product demo, and RuleTwin integration do not exist yet. The separate RuleTwin project is being developed in parallel.

The first standalone demo will answer a historical decision question, distinguish a correction from a superseding decision, display exact source citations, and abstain when evidence is missing. RuleTwin integration follows a stable, versioned evidence contract and a consumer test.

Start with the [charter](docs/product/charter.md), [corpus plan](docs/product/synthetic-corpus.md), [temporal model](docs/architecture/temporal-model.md), [implementation plan](docs/implementation-plan.md), and [progress log](docs/progress.md).

Run `python tools/validate_corpus.py` to verify the 14 synthetic source versions, 25 labeled cases, and manifest. The corpus and project are MIT licensed; see [LICENSE](LICENSE).

## Local foundation

From this repository, run `docker compose --env-file .env.example up --build -d`. The readiness shell is at `http://127.0.0.1:5174`; the API is at `http://127.0.0.1:8001/health/ready`. Load the fictional corpus with `docker compose --env-file .env.example exec -T api python -m api.app.seed`, then run `docker compose --env-file .env.example exec -T api python -m api.app.smoke`. Stop the stack with `docker compose --env-file .env.example down`; omit `-v` to retain local data. These commands are for a local synthetic demo environment only.

Run `python tools/check_all.py` for corpus, contract, credential-pattern, web-build, and Compose-configuration checks. The GitHub workflow is prepared but cannot be claimed as passed until the repository is pushed and its run is inspected.

## Boundaries

- No real customer, employer, or confidential product data.
- No answer is authoritative until source permission, temporal scope, and citation support are checked.
- Extracted decisions require human review before becoming approved decision contracts.
- DecisionTrace owns its own data. Future RuleTwin integration uses a versioned interface, never direct database access.
- The initial target is a local demo. Production or evaluation claims require reproducible evidence.
