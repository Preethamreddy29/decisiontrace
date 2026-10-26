"""Authorized temporal full-text retrieval over exact source-version chunks."""

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from .auth import Actor
from .db import connect
from .indexing import CHUNKER_VERSION
from .locks import evidence_lock_key
from .seed import stable_id


SEARCH_VERSION = "postgres-english-fts-v1"


@dataclass(frozen=True)
class SearchHit:
    source_id: str
    version_id: str
    label: str
    version: int
    kind: str
    status: str
    section_id: str
    chunk_id: str
    start_char: int
    end_char: int
    text: str
    score: float


def full_text_chunks(
    database_url: str,
    actor: Actor,
    question: str,
    valid_on: date,
    recorded_as_of: datetime,
    source_ids: list[UUID] | None = None,
    limit: int = 20,
) -> list[SearchHit]:
    """Return only exact, authorized chunks; no answer or approval is inferred."""
    if not 3 <= len(question) <= 2000 or not question.strip():
        raise ValueError("question must contain 3 to 2000 characters")
    if recorded_as_of.tzinfo is None or recorded_as_of.utcoffset() is None:
        raise ValueError("recorded_as_of must include a timezone")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be from 1 to 50")
    if source_ids is not None and not source_ids:
        return []

    sql = (
        "WITH query_terms AS (SELECT plainto_tsquery('english'::regconfig, %s) AS tsq) "
        "SELECT s.source_id, s.id, s.external_label, s.version, s.kind, s.status, "
        "c.section_id, c.chunk_id, c.start_char, c.end_char, c.content_text, "
        "c.content_sha256, c.chunker_version, s.content, s.content_sha256, "
        "ts_rank_cd(c.search_vector, q.tsq) AS score "
        "FROM source_chunks c "
        "JOIN source_versions s ON s.tenant_id = c.tenant_id AND s.id = c.source_version_id "
        "CROSS JOIN query_terms q "
        "WHERE c.tenant_id = %s AND s.tenant_id = %s AND %s = ANY(s.roles) "
        "AND s.recorded_at <= %s AND (s.superseded_at IS NULL OR s.superseded_at > %s) "
        "AND s.revoked_at IS NULL AND s.external_label IS NOT NULL "
        "AND s.valid_from <= %s AND (s.valid_to IS NULL OR s.valid_to > %s) "
        "AND c.search_vector @@ q.tsq"
    )
    tenant_id = stable_id(f"tenant/{actor.tenant}")
    values: list = [
        question, tenant_id, tenant_id, actor.role, recorded_as_of,
        recorded_as_of, valid_on, valid_on,
    ]
    if source_ids is not None:
        sql += " AND s.source_id = ANY(%s::uuid[])"
        values.append(source_ids)
    sql += " ORDER BY score DESC, s.recorded_at DESC, s.version DESC, c.chunk_id LIMIT %s"
    values.append(limit)

    with connect(database_url) as connection:
        connection.execute("SELECT pg_advisory_xact_lock_shared(%s)", (evidence_lock_key(actor),))
        rows = connection.execute(sql, values).fetchall()
        hits = []
        for row in rows:
            source_id, version_id, label, version, kind, status, section_id, chunk_id, start, end, text, chunk_sha, chunker, source, source_sha, score = row
            if chunker != CHUNKER_VERSION or text != source[start:end]:
                continue
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != chunk_sha.strip():
                continue
            if hashlib.sha256(source.encode("utf-8")).hexdigest() != source_sha.strip():
                continue
            hits.append(SearchHit(
                str(source_id), str(version_id), label, version, kind, status,
                section_id, chunk_id, start, end, text, float(score),
            ))
        return hits
