# Outbox stability checkpoint

**Date:** 2026-10-26
**Scope:** Stage A reliability work for the fictional local demo. This does not close the full v1 release gate.

## Change

- A shared registry lists every event type emitted by current protected mutations. The producer rejects an unregistered type in the same transaction as the mutation.
- The local worker validates event type, version, and payload before acknowledging it. Unknown types, malformed payloads, and future versions enter `dead_letter`. An expired lease is retried. `done` means **local validation and acknowledgement**, not delivery to an external service.
- Migration `007_outbox_version.sql` adds a version column to existing outbox rows. `contracts/events.schema.json` now describes the actual local outbox envelope; a future RuleTwin integration event contract will be separate.
- `tools/replay_outbox.py` lists valid current dead letters without changing them. `--apply` requeues only events that pass the current registry and payload check. Attempts remain recorded.
- `tools/eval_v07_outbox.py` checks every current event type, malformed and future events, unknown types, expired leases, and safe replay. It runs in the demo preflight and GitHub CI.
- Evidence queries and exact-source opening take a shared tenant lock through their read and answer-cache transaction. Protected mutations take the exclusive lock before changing evidence. This orders source revocation and corrections against in-flight answers; `tools/eval_v07_concurrency.py` checks both lock directions and post-revocation denial.

## Local replay after upgrading

First run `python tools/demo_preflight.py` to apply the migration and start the stack. Inspect eligible events with:

```powershell
docker compose --env-file .env.example exec -T api python -m tools.replay_outbox
```

Then requeue known valid events with:

```powershell
docker compose --env-file .env.example exec -T api python -m tools.replay_outbox --apply
```

The worker will acknowledge requeued events. Unknown or malformed records remain in `dead_letter` for investigation. The command affects the local database only and does not publish to another product.

## Remaining Stage A work

Exercise the current UI manually, test revocation after backup/restore, and record a clean local live stack run. Stage B then adds the planned search/model/storage/telemetry foundation. See the [portfolio completion plan](https://github.com/Preethamreddy29/enterprise-rule-intelligence/blob/codex/decisiontrace-status/docs/05_DECISIONTRACE_COMPLETION_PLAN.md).
