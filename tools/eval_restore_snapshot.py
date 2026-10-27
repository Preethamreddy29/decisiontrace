"""Verify restored evidence and revocation state in a temporary database."""

from datetime import date, datetime, timezone

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
    print("Restore smoke passed: live evidence opens, revoked evidence has no index or API/search path.")


if __name__ == "__main__":
    main()
