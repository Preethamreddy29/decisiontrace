"""Live checks for bounded, authorized full-text chunk retrieval."""

from datetime import date, datetime, timezone

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.db import connect
from api.app.retrieval import full_text_chunks
from api.app.seed import stable_id


def at(day: str) -> datetime:
    return datetime.fromisoformat(day.replace("Z", "+00:00")).astimezone(timezone.utc)


def labels(hits) -> set[str]:
    return {hit.label for hit in hits}


def main() -> None:
    database_url = load_settings().database_url
    cedar = ACCOUNTS["cedar_auditor"]
    lumen = ACCOUNTS["lumen_auditor"]
    viewer = ACCOUNTS["cedar_viewer"]

    old = full_text_chunks(database_url, cedar, "reviewer", date(2026, 5, 10), at("2026-05-10T00:00:00Z"))
    assert "SRC-MEETING-001-v1" in labels(old), labels(old)
    assert "SRC-MEETING-001-v2" not in labels(old), labels(old)

    corrected = full_text_chunks(database_url, cedar, "reviewer", date(2026, 5, 15), at("2026-05-15T00:00:00Z"))
    assert "SRC-MEETING-001-v2" in labels(corrected), labels(corrected)
    assert "SRC-MEETING-001-v1" not in labels(corrected), labels(corrected)
    assert all(hit.text and hit.score > 0 for hit in corrected)

    expired = full_text_chunks(database_url, cedar, "reviewers", date(2026, 5, 25), at("2026-05-26T00:00:00Z"),
                               source_ids=[stable_id("source/SRC-ADR-001")])
    assert expired == [], expired

    assert full_text_chunks(database_url, cedar, "Lumen manual overrides", date(2026, 5, 15),
                            at("2026-05-16T00:00:00Z")) == []
    assert "SRC-ADR-002-v1" in labels(full_text_chunks(database_url, lumen, "Lumen manual overrides",
                                                         date(2026, 5, 15), at("2026-05-16T00:00:00Z")))
    assert full_text_chunks(database_url, viewer, "manual overrides", date(2026, 5, 15),
                            at("2026-05-16T00:00:00Z")) == []

    assert full_text_chunks(database_url, cedar, "Withdrawn fictional working note", date(2026, 6, 1),
                            at("2026-06-30T00:00:00Z")) == []
    assert full_text_chunks(database_url, cedar, "reviewer", date(2026, 5, 15),
                            at("2026-05-15T00:00:00Z"), source_ids=[]) == []

    with connect(database_url) as connection:
        mismatch = connection.execute(
            "SELECT count(*) FROM source_chunks c JOIN source_versions s "
            "ON s.tenant_id = c.tenant_id AND s.id = c.source_version_id "
            "WHERE c.content_text <> substring(s.content from c.start_char + 1 for c.end_char - c.start_char)"
        ).fetchone()[0]
        assert mismatch == 0, mismatch
        revoked_chunks = connection.execute(
            "SELECT count(*) FROM source_chunks WHERE source_version_id = %s",
            (stable_id("version/SRC-REVOKED-001-v1"),),
        ).fetchone()[0]
        assert revoked_chunks == 0, revoked_chunks
    print("Full-text search passed: exact chunks, historical correction, valid time, tenant, role, and revocation.")


if __name__ == "__main__":
    main()
