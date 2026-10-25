"""Forward-only, checksummed SQL migrations for the local foundation."""

import hashlib
from pathlib import Path

from .config import load_settings
from .db import connect
from .indexing import index_source


MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
LOCK_KEY = 20261024


def migrate() -> None:
    settings = load_settings()
    with connect(settings.database_url) as connection:
        connection.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name text PRIMARY KEY, sha256 char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        connection.commit()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            row = connection.execute(
                "SELECT sha256 FROM schema_migrations WHERE name = %s", (path.name,)
            ).fetchone()
            if row:
                if row[0].strip() != digest:
                    raise RuntimeError(f"migration changed after application: {path.name}")
                continue
            # Baseline migrations contain plain SQL statements, without procedural blocks.
            for statement in raw.decode("utf-8").split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (name, sha256) VALUES (%s, %s)",
                (path.name, digest),
            )
            connection.commit()
        # Backfill only source versions that predate the persisted chunk index.
        if connection.execute("SELECT to_regclass('source_chunks')").fetchone()[0] is not None:
            rows = connection.execute(
                "SELECT s.tenant_id, s.id, s.kind, s.content FROM source_versions s "
                "WHERE NOT EXISTS (SELECT 1 FROM source_chunks c WHERE c.tenant_id = s.tenant_id "
                "AND c.source_version_id = s.id)"
            ).fetchall()
            for tenant_id, version_id, kind, content in rows:
                index_source(connection, tenant_id, version_id, kind, content)
            connection.commit()
        connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


if __name__ == "__main__":
    migrate()
    print("DecisionTrace migrations are current.")
