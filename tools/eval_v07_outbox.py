"""Exercise every current local event, invalid-event isolation, replay, and lease recovery."""

import atexit
import json
import time
from uuid import uuid4

from api.app.config import load_settings
from api.app.db import connect
from api.app.events import EVENT_TYPES
from api.app.seed import stable_id
from tools.replay_outbox import requeue_supported


def main() -> None:
    database_url = load_settings().database_url
    tenant_id = stable_id("tenant/cedar")
    event_ids = []

    def cleanup() -> None:
        if event_ids:
            with connect(database_url) as connection:
                connection.execute("DELETE FROM outbox_events WHERE id = ANY(%s::uuid[])", (event_ids,))

    atexit.register(cleanup)
    expected = {}
    with connect(database_url) as connection:
        for event_type in sorted(EVENT_TYPES):
            event_id = uuid4()
            payload = {} if event_type == "foundation.ping" else {"subject_id": str(uuid4())}
            connection.execute(
                "INSERT INTO outbox_events (id, tenant_id, event_type, payload) VALUES (%s, %s, %s, %s::jsonb)",
                (event_id, tenant_id, event_type, json.dumps(payload)),
            )
            event_ids.append(event_id)
            expected[event_id] = "done"
        unknown_id, malformed_id, future_id, expired_id, replay_id = [uuid4() for _ in range(5)]
        fixtures = (
            (unknown_id, "unsupported.future_event", 1, {"subject_id": str(uuid4())}, "pending"),
            (malformed_id, "source.revoked", 1, {"subject_id": "not-a-uuid"}, "pending"),
            (future_id, "source.revoked", 2, {"subject_id": str(uuid4())}, "pending"),
            (expired_id, "source.versioned", 1, {"subject_id": str(uuid4())}, "leased"),
            (replay_id, "change_watch.reviewed", 1, {"subject_id": str(uuid4())}, "dead_letter"),
        )
        for event_id, event_type, version, payload, state in fixtures:
            connection.execute(
                "INSERT INTO outbox_events (id, tenant_id, event_type, event_version, payload, state, lease_until) "
                "VALUES (%s, %s, %s, %s, %s::jsonb, %s, "
                "CASE WHEN %s = 'leased' THEN now() - interval '1 second' ELSE NULL END)",
                (event_id, tenant_id, event_type, version, json.dumps(payload), state, state),
            )
            event_ids.append(event_id)
            expected[event_id] = "dead_letter" if event_id in (unknown_id, malformed_id, future_id) else "done"

    assert str(replay_id) in requeue_supported(database_url), "valid dead letter missing from dry run"
    assert str(malformed_id) not in requeue_supported(database_url), "malformed event must not be replayed"
    assert str(future_id) not in requeue_supported(database_url), "future version must not be replayed"
    assert str(replay_id) in requeue_supported(database_url, apply=True), "valid dead letter was not requeued"

    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        with connect(database_url) as connection:
            rows = connection.execute(
                "SELECT id, state, attempts FROM outbox_events WHERE id = ANY(%s::uuid[])", (event_ids,),
            ).fetchall()
        if len(rows) == len(event_ids) and all(row[1] == expected[row[0]] for row in rows):
            assert all(row[2] >= 1 for row in rows if row[0] != replay_id or row[1] == "done")
            cleanup()
            print(f"Outbox passed: {len(EVENT_TYPES)} current types, invalid/future isolation, expired lease, and safe replay.")
            return
        time.sleep(0.5)
    raise AssertionError(f"Outbox states did not settle: {[(str(row[0]), row[1]) for row in rows]}")


if __name__ == "__main__":
    main()
