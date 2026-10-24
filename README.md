# DecisionTrace

DecisionTrace is a local-first product for reconstructing *why* a product decision was made, what applied at a particular time, and which versioned evidence supports the answer. All initial scenarios and data are fictional.

## Current status

Phase 0's synthetic corpus gate, the Phase 1 design gate, and the Phase 2 local foundation gate are complete. A curated Phase 3 synthetic demo now shows historical and corrected answers with inspectable source versions. Its 25 seed prompts pass status and citation checks locally. The full Phase 3 product gate, general question answering, production authorization, model, and RuleTwin integration remain open. The separate RuleTwin project is being developed in parallel.

The first standalone demo answers curated historical decision questions, distinguishes a correction from a superseding decision, displays versioned source citations, and abstains when evidence is missing. It is deterministic and limited to the frozen fictional corpus; its 25 seed prompts are not an independent holdout. RuleTwin integration follows a stable, versioned evidence contract and a consumer test.

Start with the [charter](docs/product/charter.md), [corpus plan](docs/product/synthetic-corpus.md), [temporal model](docs/architecture/temporal-model.md), [implementation plan](docs/implementation-plan.md), and [progress log](docs/progress.md).

Run `python tools/validate_corpus.py` to verify the 14 synthetic source versions, 25 labeled cases, and manifest. The corpus and project are MIT licensed; see [LICENSE](LICENSE).

## Local foundation

From this repository, run `docker compose --env-file .env.example up --build -d`. Load the fictional corpus with `docker compose --env-file .env.example exec -T api python -m api.app.seed`, then open the demo at `http://127.0.0.1:5174`. Select **Known on 10 May**, **Corrected record**, and **Current policy** to show the temporal change; open each cited source version. The API readiness endpoint is `http://127.0.0.1:8001/health/ready`. Run `docker compose --env-file .env.example exec -T api python -m api.app.smoke` and `docker compose --env-file .env.example exec -T api python -m tools.eval_demo` for local checks. Stop the stack with `docker compose --env-file .env.example down`; omit `-v` to retain local data. These commands are for a local synthetic demo environment only.

Run `python tools/check_all.py` for corpus, contract, credential-pattern, web-build, and Compose-configuration checks. The Phase 2 clean-runner evidence is recorded in [the foundation gate](docs/release/phase2-foundation-gate.md). The Phase 3 preview evaluation is recorded in [the demo preview](docs/release/phase3-demo-preview.md).

## Boundaries

- No real customer, employer, or confidential product data.
- No answer is authoritative until source permission, temporal scope, and citation support are checked.
- Extracted decisions require human review before becoming approved decision contracts.
- DecisionTrace owns its own data. Future RuleTwin integration uses a versioned interface, never direct database access.
- The initial target is a local demo. Production or evaluation claims require reproducible evidence.
