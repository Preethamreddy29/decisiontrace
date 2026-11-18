"""Live authorized keyword/vector fusion candidate comparison."""

from datetime import date, datetime, timezone

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.retrieval import full_text_chunks, hybrid_candidate_chunks, vector_chunks
from api.app.seed import stable_id


def at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    database_url = load_settings().database_url
    scenarios = [
        (ACCOUNTS["cedar_auditor"], "one reviewer", date(2026, 5, 10),
         at("2026-05-10T23:59:59Z"), stable_id("source/SRC-MEETING-001"), "SRC-MEETING-001-v1"),
        (ACCOUNTS["cedar_auditor"], "two independent reviewers", date(2026, 5, 15),
         at("2026-05-15T00:00:00Z"), stable_id("source/SRC-MEETING-001"), "SRC-MEETING-001-v2"),
        (ACCOUNTS["lumen_auditor"], "Lumen manual overrides", date(2026, 5, 15),
         at("2026-05-16T00:00:00Z"), stable_id("source/SRC-ADR-002"), "SRC-ADR-002-v1"),
    ]
    for actor, question, valid_on, recorded_as_of, source_id, label in scenarios:
        args = (database_url, actor, question, valid_on, recorded_as_of)
        lexical = full_text_chunks(*args, source_ids=[source_id], limit=5)
        vector = vector_chunks(*args, source_ids=[source_id], limit=5)
        fused = hybrid_candidate_chunks(*args, source_ids=[source_id], limit=5)
        assert lexical and vector and fused, (label, lexical, vector, fused)
        assert all(hit.label == label for hit in fused), (label, fused)
        assert all(hit.text and hit.score > 0 for hit in fused)
        print(f"{label}: lexical={len(lexical)} vector={len(vector)} hybrid={len(fused)}")

    cedar = ACCOUNTS["cedar_auditor"]
    lumen_source = stable_id("source/SRC-ADR-002")
    revoked = stable_id("source/SRC-REVOKED-001")
    assert hybrid_candidate_chunks(database_url, cedar, "Lumen manual overrides", date(2026, 5, 15),
                                   at("2026-05-16T00:00:00Z"), source_ids=[lumen_source]) == []
    assert hybrid_candidate_chunks(database_url, cedar, "withdrawn fictional note", date(2026, 6, 1),
                                   at("2026-06-30T00:00:00Z"), source_ids=[revoked]) == []
    assert hybrid_candidate_chunks(database_url, cedar, "reviewer", date(2026, 5, 15),
                                   at("2026-05-15T00:00:00Z"), source_ids=[]) == []
    print("Hybrid candidate gate passed: one-snapshot fusion, historical scope, tenant denial, revocation.")


if __name__ == "__main__":
    main()
