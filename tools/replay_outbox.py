"""Inspect or requeue valid local outbox events previously dead-lettered by the old worker."""

import argparse

from api.app.config import load_settings
from api.app.db import connect
from api.app.events import valid_event


def requeue_supported(database_url: str, apply: bool = False) -> list[str]:
    with connect(database_url) as connection:
        rows = connection.execute(
            "SELECT id, event_type, event_version, payload FROM outbox_events "
            "WHERE state = 'dead_letter' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 500"
        ).fetchall()
        event_ids = [row[0] for row in rows if valid_event(row[1], row[2], row[3])]
        if apply and event_ids:
            connection.execute(
                "UPDATE outbox_events SET state = 'pending', lease_until = NULL "
                "WHERE id = ANY(%s::uuid[]) AND state = 'dead_letter'", (event_ids,),
            )
        return [str(event_id) for event_id in event_ids]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Requeue valid current events; otherwise show a dry run")
    args = parser.parse_args()
    event_ids = requeue_supported(load_settings().database_url, apply=args.apply)
    action = "Requeued" if args.apply else "Eligible for replay"
    print(f"{action}: {len(event_ids)} local outbox event(s).")


if __name__ == "__main__":
    main()
