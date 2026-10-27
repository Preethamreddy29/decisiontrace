"""Live index-rebuild drill with a missing chunk and stale revoked chunk."""

from datetime import date, datetime, timezone

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.db import connect
from api.app.indexing import index_source
from api.app.retrieval import full_text_chunks
from api.app.seed import stable_id
from tools.rebuild_index import rebuild_index


def main() -> None:
    database_url = load_settings().database_url
    tenant_id = stable_id("tenant/cedar")
    live_version = stable_id("version/SRC-MEETING-001-v2")
    live_source = stable_id("source/SRC-MEETING-001")
    revoked_version = stable_id("version/SRC-REVOKED-001-v1")
    revoked_source = stable_id("source/SRC-REVOKED-001")
    actor = ACCOUNTS["cedar_auditor"]

    baseline = rebuild_index(database_url)
    assert baseline["repaired_versions"] == 0 and baseline["removed_revoked_chunks"] == 0, baseline
    try:
        with connect(database_url) as connection:
            connection.execute(
                "DELETE FROM source_chunks WHERE tenant_id = %s AND source_version_id = %s",
                (tenant_id, live_version),
            )
            kind, content = connection.execute(
                "SELECT kind, content FROM source_versions WHERE tenant_id = %s AND id = %s",
                (tenant_id, revoked_version),
            ).fetchone()
            assert index_source(connection, tenant_id, revoked_version, kind, content) > 0

        before = rebuild_index(database_url)
        assert before["repaired_versions"] >= 1 and before["removed_revoked_chunks"] >= 1, before
        with connect(database_url) as connection:
            assert connection.execute(
                "SELECT count(*) FROM source_chunks WHERE source_version_id = %s",
                (live_version,),
            ).fetchone()[0] == 0
            assert connection.execute(
                "SELECT count(*) FROM source_chunks WHERE source_version_id = %s",
                (revoked_version,),
            ).fetchone()[0] > 0

        assert full_text_chunks(
            database_url, actor, "Withdrawn fictional working note", date(2026, 6, 1),
            datetime(2026, 6, 30, tzinfo=timezone.utc), source_ids=[revoked_source],
        ) == []

        applied = rebuild_index(database_url, apply=True)
        assert applied["repaired_versions"] >= 1 and applied["removed_revoked_chunks"] >= 1, applied
        clean = rebuild_index(database_url)
        assert clean["repaired_versions"] == 0 and clean["removed_revoked_chunks"] == 0, clean
        hits = full_text_chunks(
            database_url, actor, "two independent reviewers", date(2026, 5, 15),
            datetime(2026, 5, 15, tzinfo=timezone.utc), source_ids=[live_source],
        )
        assert any(hit.version_id == str(live_version) for hit in hits), hits
    finally:
        rebuild_index(database_url, apply=True)
    print("Index rebuild passed: dry-run detection, authorized repair, revoked purge, and exact retrieval.")


if __name__ == "__main__":
    main()
