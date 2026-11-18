"""Live gate for the pinned pgvector baseline and authorized temporal retrieval."""

from datetime import date, datetime, timezone

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.db import connect
from api.app.embedding import DIMENSIONS, PROFILE, vector_checksum, vector_literal
from api.app.retrieval import vector_chunks
from api.app.seed import stable_id
from tools.rebuild_index import rebuild_index


def at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    database_url = load_settings().database_url
    cedar = ACCOUNTS["cedar_auditor"]
    lumen = ACCOUNTS["lumen_auditor"]
    viewer = ACCOUNTS["cedar_viewer"]
    meeting = stable_id("source/SRC-MEETING-001")
    revoked = stable_id("source/SRC-REVOKED-001")
    lumen_source = stable_id("source/SRC-ADR-002")

    vector = vector_literal("Two independent reviewers")
    assert vector and len(vector.split(",")) == DIMENSIONS
    assert vector == vector_literal("reviewers independent two")
    assert vector_checksum(vector) == vector_checksum(vector_literal("two reviewers independent"))

    with connect(database_url) as connection:
        extension = connection.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()
        assert extension is not None, "pgvector extension missing"
        missing = connection.execute(
            "SELECT count(*) FROM source_chunks WHERE embedding_profile IS DISTINCT FROM %s "
            "OR (embedding IS NOT NULL AND embedding_sha256 IS NULL)",
            (PROFILE,),
        ).fetchone()[0]
        assert missing == 0, missing

    old = vector_chunks(database_url, cedar, "reviewer", date(2026, 5, 10),
                        at("2026-05-10T00:00:00Z"), source_ids=[meeting])
    assert old and all(hit.label == "SRC-MEETING-001-v1" for hit in old), old

    corrected = vector_chunks(database_url, cedar, "two independent reviewers", date(2026, 5, 15),
                              at("2026-05-15T00:00:00Z"), source_ids=[meeting])
    assert corrected and all(hit.label == "SRC-MEETING-001-v2" for hit in corrected), corrected
    assert all(hit.score >= 0 for hit in corrected)
    assert vector_chunks(database_url, cedar, "reviewer", date(2026, 5, 15),
                         at("2026-05-15T00:00:00Z"), source_ids=[revoked]) == []
    assert vector_chunks(database_url, viewer, "manual overrides", date(2026, 5, 15),
                         at("2026-05-16T00:00:00Z")) == []
    assert vector_chunks(database_url, cedar, "Lumen manual overrides", date(2026, 5, 15),
                         at("2026-05-16T00:00:00Z"), source_ids=[lumen_source]) == []
    lumen_hits = vector_chunks(database_url, lumen, "Lumen manual overrides", date(2026, 5, 15),
                               at("2026-05-16T00:00:00Z"), source_ids=[lumen_source])
    assert lumen_hits and all(hit.source_id == str(lumen_source) for hit in lumen_hits)
    assert vector_chunks(database_url, cedar, "reviewer", date(2026, 5, 15),
                         at("2026-05-15T00:00:00Z"), source_ids=[]) == []

    target = corrected[0]
    assert rebuild_index(database_url)["repaired_versions"] == 0
    try:
        with connect(database_url) as connection:
            connection.execute(
                "UPDATE source_chunks SET embedding = %s::vector WHERE source_version_id = %s AND chunk_id = %s",
                ("[" + ",".join(["1"] + ["0"] * (DIMENSIONS - 1)) + "]",
                 target.version_id, target.chunk_id),
            )
        before = rebuild_index(database_url)
        assert before["repaired_versions"] >= 1, before
        damaged = vector_chunks(database_url, cedar, "two independent reviewers", date(2026, 5, 15),
                                at("2026-05-15T00:00:00Z"), source_ids=[meeting])
        assert target.chunk_id not in {hit.chunk_id for hit in damaged}, damaged
        assert rebuild_index(database_url, apply=True)["repaired_versions"] >= 1
        assert rebuild_index(database_url)["repaired_versions"] == 0
    finally:
        rebuild_index(database_url, apply=True)
    print("Vector gate passed: pinned profile, time/tenant/role/revocation, exact chunks, and rebuild.")


if __name__ == "__main__":
    main()
