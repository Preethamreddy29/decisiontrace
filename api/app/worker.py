"""Lease-based local validation and acknowledgement of current outbox events."""

import logging
import time

from .config import load_settings
from .db import connect
from .events import valid_event


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("decisiontrace.worker")


def claim_once(database_url: str):
    with connect(database_url) as connection:
        row = connection.execute(
            "SELECT id, event_type, event_version, payload FROM outbox_events "
            "WHERE state = 'pending' OR (state = 'leased' AND lease_until < now()) "
            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "UPDATE outbox_events SET state = 'leased', "
            "lease_until = now() + interval '30 seconds', attempts = attempts + 1 WHERE id = %s",
            (row[0],),
        )
        return row


def finish(database_url: str, event_id, event_type: str, event_version: int, payload: object) -> None:
    state = "done" if valid_event(event_type, event_version, payload) else "dead_letter"
    with connect(database_url) as connection:
        connection.execute(
            "UPDATE outbox_events SET state = %s, lease_until = NULL "
            "WHERE id = %s AND state = 'leased'",
            (state, event_id),
        )
    if state == "dead_letter":
        logger.error("unsupported outbox event id=%s type=%s", event_id, event_type)


def run() -> None:
    database_url = load_settings().database_url
    logger.info("worker started")
    while True:
        try:
            item = claim_once(database_url)
            if item:
                finish(database_url, item[0], item[1], item[2], item[3])
            else:
                time.sleep(2)
        except Exception:
            logger.exception("outbox poll failed")
            time.sleep(3)


if __name__ == "__main__":
    run()
