"""Local foundation smoke: schema, seed, and live worker outbox delivery."""

import time
from uuid import uuid4

from .config import load_settings
from .db import connect, is_ready
from .seed import seed, stable_id


def smoke() -> None:
    database_url = load_settings().database_url
    if not is_ready(database_url):
        raise RuntimeError("database or migrations not ready")
    seed()
    with connect(database_url) as connection:
        tenants = connection.execute("SELECT count(*) FROM tenants").fetchone()[0]
        sources = connection.execute("SELECT count(*) FROM source_versions").fetchone()[0]
        labeled = connection.execute("SELECT count(*) FROM source_versions WHERE external_label IS NOT NULL").fetchone()[0]
        migrations = connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
        if (tenants, sources, labeled, migrations) != (2, 14, 14, 2):
            raise RuntimeError(f"unexpected foundation counts: {(tenants, sources, labeled, migrations)}")
        event_id = uuid4()
        connection.execute(
            "INSERT INTO outbox_events (id, tenant_id, event_type, payload) "
            "VALUES (%s, %s, 'foundation.ping', '{}'::jsonb)",
            (event_id, stable_id("tenant/cedar")),
        )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        with connect(database_url) as connection:
            state = connection.execute(
                "SELECT state FROM outbox_events WHERE id = %s", (event_id,)
            ).fetchone()[0]
        if state == "done":
            print("Foundation smoke passed: 2 tenants, 14 labeled source versions, 2 migrations, worker delivery.")
            return
        if state == "dead_letter":
            raise RuntimeError("foundation ping was rejected by worker")
        time.sleep(0.5)
    raise RuntimeError("worker did not finish foundation ping within 20 seconds")


if __name__ == "__main__":
    smoke()
