# Phase 3 Curated Demo Preview

**State:** local preview verified on 2026-10-24; the full Phase 3 product gate remains open.

The local page at `http://127.0.0.1:5174` presents curated fictional Cedar scenarios: what was known on 10 May, the corrected record, the policy after supersession, drift, an unapproved conflicting draft, and evidence-backed abstention. Each answer exposes the source versions used. The demo API is `/demo/query`, deliberately separate from the planned authenticated `/v1/query` contract. The tenant and role in its request are simulation controls and provide no real authorization boundary.

The resolver reads stored source versions after filtering tenant, role, recorded time, revocation, and supersession. It checks stored content against the frozen fictional fixture before a curated answer can cite it. It does not call a model or perform general retrieval. Unsupported questions abstain.

## Local proof

- `python tools/check_all.py` passes the static checks and web build.
- The Compose stack starts with healthy database and API services.
- `docker compose --env-file .env.example exec -T api python -m tools.eval_demo` passes all 25 authored seed cases for status and required citation IDs. It also checks critical answer phrases, excludes the 12 May correction from a 10 May recorded-time answer, and abstains on an unsupported question.
- A query through the web proxy returned the then-recorded one-reviewer answer with only `SRC-MEETING-001-v1` cited.
- [GitHub Actions run 40058446722](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40058446722) passed from a clean checkout of demo commit `9fe787e`, including the 25-case evaluation step.

## Open before the full Phase 3 gate

The 25 seed prompts are authored in the same repository and are not an independent holdout. The resolver uses curated rules and full-source citations; it does not implement the versioned `/v1/query` claim-level contract, actual authentication, general question answering, or independent answer-quality evaluation. The UI is a controlled demo, not a production decision tool.
