"""Load the fictional seed corpus idempotently into the local database."""

import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .config import load_settings
from .db import connect
from .indexing import index_source


CORPUS_PATH = Path(__file__).resolve().parents[2] / "corpus" / "sources.json"


def stable_id(label: str):
    return uuid5(NAMESPACE_URL, f"decisiontrace-synthetic/{label}")


def seed() -> None:
    document = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if not document.get("fictional"):
        raise RuntimeError("seed loader accepts only the fictional corpus")
    settings = load_settings()
    with connect(settings.database_url) as connection:
        for name in sorted({item["tenant"] for item in document["sources"]}):
            connection.execute(
                "INSERT INTO tenants (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (stable_id(f"tenant/{name}"), name),
            )
        for item in document["sources"]:
            digest = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
            source_version_id = stable_id(f"version/{item['id']}")
            existing = connection.execute(
                "SELECT content_sha256 FROM source_versions WHERE id = %s", (source_version_id,)
            ).fetchone()
            if existing:
                if existing[0].strip() != digest:
                    raise RuntimeError(f"seed content changed without version: {item['id']}")
                connection.execute(
                    "UPDATE source_versions SET external_label = %s WHERE id = %s "
                    "AND (external_label IS NULL OR external_label = %s)",
                    (item["id"], source_version_id, item["id"]),
                )
                index_source(connection, stable_id(f"tenant/{item['tenant']}"), source_version_id, item["kind"], item["text"])
                continue
            connection.execute(
                "INSERT INTO source_versions "
                "(id, source_id, tenant_id, version, kind, recorded_at, valid_from, valid_to, "
                "status, content_sha256, content, roles, revoked_at, superseded_at, external_label) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    source_version_id,
                    stable_id(f"source/{item['source_id']}"),
                    stable_id(f"tenant/{item['tenant']}"),
                    item["version"], item["kind"], item["recorded_at"],
                    item["valid_from"], item.get("valid_to"), item["status"],
                    digest, item["text"], item["roles"], item.get("revoked_at"),
                    item.get("superseded_at"), item["id"],
                ),
            )
            index_source(connection, stable_id(f"tenant/{item['tenant']}"), source_version_id, item["kind"], item["text"])


if __name__ == "__main__":
    seed()
    print("DecisionTrace fictional corpus is loaded.")
