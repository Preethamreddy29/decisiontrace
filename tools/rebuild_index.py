"""Inspect and repair exact source chunks without changing source history."""

import argparse
import hashlib
import json

from api.app.auth import Actor
from api.app.config import load_settings
from api.app.db import connect
from api.app.indexing import CHUNKER_VERSION, chunk_source, index_source
from api.app.locks import evidence_lock_key
from api.app.retrieval import SEARCH_VERSION


def rebuild_index(database_url: str, *, tenant: str | None = None, apply: bool = False) -> dict:
    with connect(database_url) as connection:
        if connection.execute("SELECT to_regclass('source_chunks')").fetchone()[0] is None:
            raise RuntimeError("source_chunks migration is not applied")
        tenants = connection.execute(
            "SELECT id, name FROM tenants WHERE (%s::text IS NULL OR name = %s) ORDER BY name",
            (tenant, tenant),
        ).fetchall()
    if tenant is not None and not tenants:
        raise ValueError("unknown tenant")

    result = {
        "mode": "apply" if apply else "dry_run",
        "chunker_version": CHUNKER_VERSION,
        "search_version": SEARCH_VERSION,
        "tenants": len(tenants),
        "checked_versions": 0,
        "repaired_versions": 0,
        "removed_revoked_chunks": 0,
    }
    for tenant_id, tenant_name in tenants:
        with connect(database_url) as connection:
            lock = "pg_advisory_xact_lock" if apply else "pg_advisory_xact_lock_shared"
            connection.execute(f"SELECT {lock}(%s)", (evidence_lock_key(Actor("index-rebuild", tenant_name, "owner")),))
            versions = connection.execute(
                "SELECT id, kind, content, content_sha256, revoked_at "
                "FROM source_versions WHERE tenant_id = %s ORDER BY id",
                (tenant_id,),
            ).fetchall()
            for version_id, kind, content, source_sha, revoked_at in versions:
                result["checked_versions"] += 1
                actual = [
                    (row[0], row[1], row[2], row[3], row[4].strip(), row[5], row[6])
                    for row in connection.execute(
                        "SELECT chunk_id, section_id, start_char, end_char, content_sha256, "
                        "chunker_version, content_text FROM source_chunks "
                        "WHERE tenant_id = %s AND source_version_id = %s ORDER BY chunk_id",
                        (tenant_id, version_id),
                    ).fetchall()
                ]
                if revoked_at is not None:
                    result["removed_revoked_chunks"] += len(actual)
                    if actual and apply:
                        connection.execute(
                            "DELETE FROM source_chunks WHERE tenant_id = %s AND source_version_id = %s",
                            (tenant_id, version_id),
                        )
                    continue
                if hashlib.sha256(content.encode("utf-8")).hexdigest() != source_sha.strip():
                    raise RuntimeError(f"source version {version_id} failed its checksum")
                expected = sorted(
                    (chunk.chunk_id, chunk.section_id, chunk.start_char, chunk.end_char,
                     chunk.sha256, CHUNKER_VERSION, chunk.content_text)
                    for chunk in chunk_source(kind, content)
                )
                if actual != expected:
                    result["repaired_versions"] += 1
                    if apply:
                        index_source(connection, tenant_id, version_id, kind, content)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or repair DecisionTrace's exact source-chunk index")
    parser.add_argument("--apply", action="store_true", help="repair mismatches; default is read-only")
    parser.add_argument("--tenant", help="restrict work to one known tenant")
    args = parser.parse_args()
    result = rebuild_index(load_settings().database_url, tenant=args.tenant, apply=args.apply)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
