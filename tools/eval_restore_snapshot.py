"""Verify restored evidence and revocation state in a temporary database."""

from datetime import date, datetime, timedelta, timezone
import os

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.db import connect
from api.app.query import open_evidence
from api.app.retrieval import full_text_chunks
from api.app.seed import stable_id


def main() -> None:
    url = load_settings().database_url
    actor = ACCOUNTS["cedar_auditor"]
    as_of = datetime(2026, 6, 30, tzinfo=timezone.utc)
    revoked_source = stable_id("source/SRC-REVOKED-001")
    revoked_version = stable_id("version/SRC-REVOKED-001-v1")

    with connect(url) as connection:
        row = connection.execute(
            "SELECT revoked_at FROM source_versions WHERE tenant_id = %s AND id = %s",
            (stable_id("tenant/cedar"), revoked_version),
        ).fetchone()
        assert row and row[0] is not None, row
        chunks = connection.execute(
            "SELECT count(*) FROM source_chunks WHERE tenant_id = %s AND source_version_id = %s",
            (stable_id("tenant/cedar"), revoked_version),
        ).fetchone()[0]
        assert chunks == 0, chunks

    assert open_evidence(url, actor, revoked_source, revoked_version, as_of) is None
    assert full_text_chunks(url, actor, "Withdrawn fictional working note", date(2026, 6, 1), as_of) == []

    live_source = stable_id("source/SRC-MEETING-001")
    live_version = stable_id("version/SRC-MEETING-001-v2")
    opened = open_evidence(url, actor, live_source, live_version, as_of)
    assert opened and opened["version_id"] == str(live_version), opened
    hits = full_text_chunks(url, actor, "two independent reviewers", date(2026, 5, 15), as_of,
                            source_ids=[live_source])
    assert any(hit.version_id == str(live_version) for hit in hits), hits
    token = os.environ.get("RESTORE_EVAL_ID", "")
    assert len(token) == 12 and all(char in "0123456789abcdef" for char in token)
    with connect(url) as connection:
        row = connection.execute(
            "SELECT source_id, id, revoked_at FROM source_versions WHERE tenant_id = %s AND origin = %s",
            (stable_id("tenant/cedar"), f"__restore_eval__/{token}"),
        ).fetchone()
        assert row and row[2] is not None, row
        dynamic_source, dynamic_version = row[:2]
        assert connection.execute(
            "SELECT count(*) FROM source_chunks WHERE source_version_id = %s",
            (dynamic_version,),
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM audit_events WHERE tenant_id = %s AND action = 'source.revoked' AND subject_id = %s",
            (stable_id("tenant/cedar"), dynamic_version),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM outbox_events WHERE tenant_id = %s AND event_type = 'source.revoked' "
            "AND payload->>'subject_id' = %s",
            (stable_id("tenant/cedar"), str(dynamic_version)),
        ).fetchone()[0] == 1
    after_revocation = datetime.now(timezone.utc) + timedelta(seconds=1)
    assert open_evidence(url, actor, dynamic_source, dynamic_version, after_revocation) is None
    assert full_text_chunks(url, actor, "fictional Cedar approval restore", date(2026, 7, 1), after_revocation,
                            source_ids=[dynamic_source]) == []
    print("Restore smoke passed: live evidence opens; seeded and API-revoked evidence, audit, and outbox survive correctly.")


if __name__ == "__main__":
    main()
