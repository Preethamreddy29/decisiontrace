"""Bounded, database-backed decision queries for the synthetic v0.2 demo.

Answers quote exact source sentences. This deliberately supports a small set of
decision questions and abstains outside that scope; it does not use a model.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import Actor
from .db import connect
from .seed import stable_id


CORPUS_VERSION = "dt-synthetic-v0.1"
PIPELINE = {"retrieval": "temporal-relational-v0.2", "answer": "exact-source-sentence-v0.2"}


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=2000)
    valid_on: date | None = None
    recorded_as_of: datetime
    source_ids: list[UUID] | None = Field(default=None, max_length=50)
    answer_mode: Literal["structured"] = "structured"

    @field_validator("recorded_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_as_of must include a timezone")
        return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Source:
    source_id: str
    version_id: str
    label: str
    version: int
    kind: str
    recorded_at: datetime
    valid_from: date
    valid_to: date | None
    status: str
    content: str
    sha256: str


def visible_sources(database_url: str, actor: Actor, as_of: datetime, source_ids: list[UUID] | None = None) -> list[Source]:
    sql = (
        "SELECT source_id, id, external_label, version, kind, recorded_at, valid_from, "
        "valid_to, status, content, content_sha256 FROM source_versions "
        "WHERE tenant_id = %s AND %s = ANY(roles) AND recorded_at <= %s "
        "AND revoked_at IS NULL AND (superseded_at IS NULL OR superseded_at > %s)"
    )
    values: list = [stable_id(f"tenant/{actor.tenant}"), actor.role, as_of, as_of]
    if source_ids is not None:
        if not source_ids:
            return []
        sql += " AND source_id = ANY(%s::uuid[])"
        values.append(source_ids)
    sql += " ORDER BY recorded_at DESC, version DESC"
    with connect(database_url) as connection:
        rows = connection.execute(sql, values).fetchall()
    result = []
    for row in rows:
        digest = hashlib.sha256(row[9].encode("utf-8")).hexdigest()
        if row[2] is None or digest != row[10].strip():
            continue  # An unlabeled or corrupted version is not answer evidence.
        result.append(Source(
            source_id=str(row[0]), version_id=str(row[1]), label=row[2], version=row[3],
            kind=row[4], recorded_at=row[5], valid_from=row[6], valid_to=row[7],
            status=row[8], content=row[9], sha256=digest,
        ))
    return result


def _sentence(source: Source, *required: str) -> str | None:
    for match in re.finditer(r"[^.!?]+[.!?]?", source.content):
        candidate = match.group().strip()
        if candidate and all(term in candidate.lower() for term in required):
            return candidate
    return None


def _claim(source: Source, sentence: str, decision_version_id: str | None = None) -> dict:
    start = source.content.find(sentence)
    if start < 0:
        raise RuntimeError("citation quote is not in its source version")
    result = {
        "text": sentence,
        "citations": [{
            "source_id": source.source_id, "version_id": source.version_id,
            "section_id": "body", "label": source.label, "quote": sentence,
            "start_char": start, "end_char": start + len(sentence),
        }],
    }
    if decision_version_id:
        result["decision_version_id"] = decision_version_id
    return result


def _approved_policy(database_url: str, actor: Actor, valid_on: date, as_of: datetime):
    """Return the newest reviewed manual-override decision, if one existed then."""
    with connect(database_url) as connection:
        return connection.execute(
            "SELECT d.id, d.evidence_version_ids FROM decision_versions d WHERE d.tenant_id = %s "
            "AND d.status = 'approved' AND d.valid_from <= %s AND (d.valid_to IS NULL OR d.valid_to > %s) "
            "AND d.recorded_at <= %s AND d.title ILIKE %s "
            "AND NOT EXISTS (SELECT 1 FROM unnest(d.evidence_version_ids) evidence(id) "
            "WHERE NOT EXISTS (SELECT 1 FROM source_versions s WHERE s.id = evidence.id "
            "AND s.tenant_id = d.tenant_id AND %s = ANY(s.roles) AND s.revoked_at IS NULL)) "
            "ORDER BY d.valid_from DESC, d.recorded_at DESC LIMIT 1",
            (stable_id(f"tenant/{actor.tenant}"), valid_on, valid_on, as_of, "%manual override%", actor.role),
        ).fetchone()


def _policy(sources: list[Source], valid_on: date, as_of: datetime) -> Source | None:
    approved = [source for source in sources if source.kind == "adr" and source.status == "approved"
                and source.valid_from <= valid_on and (source.valid_to is None or valid_on < source.valid_to)
                and "manual override" in source.content.lower()]
    if approved:
        return max(approved, key=lambda source: (source.valid_from, source.recorded_at))
    # A meeting record is only a fallback for a date already reached when it
    # was queried. Otherwise an old transcript could invent a future policy.
    if valid_on > as_of.date() or valid_on < date(2026, 5, 1):
        return None
    meetings = [source for source in sources if source.kind == "meeting"
                and source.status in ("recorded", "corrected_record")
                and source.valid_from <= valid_on and "manual override" in source.content.lower()]
    return max(meetings, key=lambda source: source.recorded_at) if meetings else None


def _empty(status: str, reason: str, query: QueryRequest, valid_on: date) -> dict:
    return {
        "answer_id": str(uuid4()), "status": status, "claims": [],
        "conflict_summary": None, "abstention_reason": reason,
        "corpus_or_index_version": CORPUS_VERSION,
        "recorded_as_of": query.recorded_as_of.isoformat(), "valid_on": valid_on.isoformat(),
        "pipeline_versions": PIPELINE,
    }


def resolve(database_url: str, actor: Actor, query: QueryRequest) -> dict:
    valid_on = query.valid_on or query.recorded_as_of.date()
    question = re.sub(r"[^a-z0-9]+", " ", query.question.lower()).strip()
    terms = set(question.split())
    other_tenant = "lumen" if actor.tenant == "cedar" else "cedar"
    if other_tenant in terms:
        return _empty("denied", "The requested tenant is outside this demo account.", query, valid_on)
    if "why" in terms or "undocumented" in terms:
        return _empty("abstain", "No permitted evidence establishes a reason.", query, valid_on)

    sources = visible_sources(database_url, actor, query.recorded_as_of, query.source_ids)
    claims: list[dict] = []
    status = "answered"
    summary = None

    if terms & {"test", "tests", "drift", "implementation"}:
        test = next((s for s in sources if s.kind == "test" and s.status == "active"), None)
        policy = _policy(sources, valid_on, query.recorded_as_of)
        if test and policy:
            test_quote = _sentence(test, "stale") or _sentence(test, "still expects")
            policy_quote = _sentence(policy, "manual overrides", "disabled")
            if test_quote and policy_quote:
                claims = [_claim(test, test_quote), _claim(policy, policy_quote)]
                status, summary = "conflict", "The active test differs from the approved policy."
    elif terms & {"draft", "conflict", "contradiction", "consistent"}:
        draft = next((s for s in sources if s.status == "draft"), None)
        policy = _policy(sources, valid_on, query.recorded_as_of)
        if draft and policy:
            draft_quote = _sentence(draft, "conflicts") or _sentence(draft, "unapproved")
            policy_quote = _sentence(policy, "manual overrides", "disabled")
            if draft_quote and policy_quote:
                claims = [_claim(draft, draft_quote), _claim(policy, policy_quote)]
                status, summary = "conflict", "An unapproved draft conflicts with the approved policy."
    elif terms & {"correction", "corrected", "transcript", "misrecorded"}:
        corrected = next((s for s in sources if s.kind == "meeting" and s.status == "corrected_record"), None)
        if corrected:
            quote = _sentence(corrected, "two independent reviewers")
            if quote:
                claims = [_claim(corrected, quote)]
    elif terms & {"supersede", "superseded", "superseding", "replace", "replaced", "replacement"} or "new decision" in question or "effective date" in question:
        decisions = [s for s in sources if s.kind == "adr" and s.status == "approved" and "supersedes" in s.content.lower()]
        if decisions:
            decision = max(decisions, key=lambda s: s.recorded_at)
            quote = _sentence(decision, "supersedes")
            if quote:
                claims = [_claim(decision, quote)]
    elif terms & {"override", "overrides", "reviewer", "reviewers", "signoff", "signoffs"} or "sign off" in question or "manual adjustment" in question:
        reviewed = _approved_policy(database_url, actor, valid_on, query.recorded_as_of)
        if reviewed:
            matching = [source for source in sources if UUID(source.version_id) in reviewed[1]]
            if len(matching) != len(reviewed[1]):
                return _empty("abstain", "The approved decision's exact evidence is no longer available.", query, valid_on)
            policy = next((source for source in matching if "manual override" in source.content.lower()), None)
            if policy:
                quote = _sentence(policy, "manual override")
                if quote:
                    claims = [_claim(policy, quote, str(reviewed[0]))]
        else:
            policy = _policy(sources, valid_on, query.recorded_as_of)
            if policy:
                quote = _sentence(policy, "manual override")
                if quote:
                    claims = [_claim(policy, quote)]

    if not claims:
        return _empty("abstain", "No permitted source version supports this question at the selected times.", query, valid_on)
    return {
        "answer_id": str(uuid4()), "status": status, "claims": claims,
        "conflict_summary": summary, "abstention_reason": None,
        "corpus_or_index_version": CORPUS_VERSION,
        "recorded_as_of": query.recorded_as_of.isoformat(), "valid_on": valid_on.isoformat(),
        "pipeline_versions": PIPELINE,
    }


def query_with_idempotency(database_url: str, actor: Actor, query: QueryRequest, key: str) -> dict:
    if not 8 <= len(key) <= 128 or not re.fullmatch(r"[A-Za-z0-9._-]+", key):
        raise HTTPException(status_code=422, detail="Invalid Idempotency-Key")
    payload = json.dumps(query.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with connect(database_url) as connection:
        existing = connection.execute(
            "SELECT request_sha256, answer FROM query_requests WHERE actor_id = %s AND idempotency_key = %s",
            (actor.account, key),
        ).fetchone()
    if existing:
        if existing[0].strip() != digest:
            raise HTTPException(status_code=409, detail="Idempotency-Key was used for a different query")
        current = {s.version_id: s for s in visible_sources(database_url, actor, query.recorded_as_of, query.source_ids)}
        if any(
            c["version_id"] not in current or
            current[c["version_id"]].content[c["start_char"]:c["end_char"]] != c["quote"]
            for claim in existing[1]["claims"] for c in claim["citations"]
        ):
            raise HTTPException(status_code=409, detail="Stored answer references evidence that is no longer available")
        return existing[1]

    answer = resolve(database_url, actor, query)
    with connect(database_url) as connection:
        connection.execute(
            "INSERT INTO query_requests (actor_id, idempotency_key, request_sha256, answer) "
            "VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT DO NOTHING",
            (actor.account, key, digest, json.dumps(answer)),
        )
        stored = connection.execute(
            "SELECT request_sha256, answer FROM query_requests WHERE actor_id = %s AND idempotency_key = %s",
            (actor.account, key),
        ).fetchone()
    if stored[0].strip() != digest:
        raise HTTPException(status_code=409, detail="Idempotency-Key was used for a different query")
    return stored[1]


def open_evidence(database_url: str, actor: Actor, source_id: UUID, version_id: UUID, as_of: datetime) -> dict | None:
    for source in visible_sources(database_url, actor, as_of):
        if source.source_id == str(source_id) and source.version_id == str(version_id):
            return {
                "source_id": source.source_id, "version_id": source.version_id,
                "external_label": source.label, "version": source.version, "kind": source.kind,
                "sha256": source.sha256, "recorded_at": source.recorded_at.isoformat(),
                "valid_from": source.valid_from.isoformat(),
                "valid_to": source.valid_to.isoformat() if source.valid_to else None,
                "status": source.status, "content": source.content,
            }
    return None
