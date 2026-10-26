"""Governed text-source and human decision workflow for the local synthetic demo."""

import hashlib
import json
import re
from datetime import date
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .auth import ACCOUNTS, Actor, actor_scope
from .db import connect
from .seed import stable_id
from .sections import parse_sections
from .indexing import index_source
from .events import EVENT_TYPES
from .locks import evidence_lock_key


KEY_PATTERN = re.compile(r"[A-Za-z0-9._-]{8,128}\Z")
SOURCE_COLUMNS = (
    "id, source_id, version, kind, content_sha256, recorded_at, status, "
    "external_label, valid_from, valid_to, content, origin, created_by, roles, superseded_at, revoked_at"
)
DECISION_COLUMNS = (
    "id, decision_id, version, status, valid_from, valid_to, recorded_at, "
    "owner_id, approver_id, evidence_version_ids, title, supersedes_decision_id"
)


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["markdown", "transcript", "json"]
    origin: str = Field(min_length=3, max_length=500)
    content: str = Field(min_length=15, max_length=10000)
    valid_from: date
    valid_to: date | None = None
    permissions: list[Literal["owner", "engineer", "qa", "auditor", "viewer"]] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must follow valid_from")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("permissions must be unique")
        if self.kind == "json":
            try:
                json.loads(self.content)
            except json.JSONDecodeError as exc:
                raise ValueError("json source content must be valid JSON") from exc
        return self


class ConnectorSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remote_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,120}$")
    remote_version: str = Field(pattern=r"^[A-Za-z0-9._-]{1,120}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: SourceCreate


class DecisionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=8, max_length=300)
    valid_from: date
    valid_to: date | None = None
    evidence_version_ids: list[UUID] = Field(min_length=1, max_length=10)
    supersedes_decision_id: UUID | None = None

    @model_validator(mode="after")
    def valid_interval(self):
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must follow valid_from")
        if len(set(self.evidence_version_ids)) != len(self.evidence_version_ids):
            raise ValueError("evidence versions must be unique")
        return self


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=2000)


class SourceRevocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=8, max_length=500)


def _require_author(actor: Actor):
    if actor.role not in ("owner", "auditor"):
        raise HTTPException(status_code=403, detail="This demo identity cannot author evidence")


def _require_reviewer(actor: Actor):
    if actor.role != "auditor":
        raise HTTPException(status_code=403, detail="An auditor identity must review this decision")


def _mutation(database_url: str, actor: Actor, operation: str, key: str, request: dict, perform):
    if not KEY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Invalid Idempotency-Key")
    payload = json.dumps(request, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    scoped_actor = actor_scope(actor)
    lock_value = int.from_bytes(hashlib.sha256(f"{scoped_actor}/{operation}/{key}".encode()).digest()[:8], "big", signed=True)
    with connect(database_url) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (evidence_lock_key(actor),))
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (lock_value,))
        prior = connection.execute(
            "SELECT request_sha256, response FROM mutation_requests "
            "WHERE actor_id = %s AND operation = %s AND idempotency_key = %s",
            (scoped_actor, operation, key),
        ).fetchone()
        if prior:
            if prior[0].strip() != digest:
                raise HTTPException(status_code=409, detail="Idempotency-Key was used for another mutation")
            return prior[1]
        response = perform(connection)
        connection.execute(
            "INSERT INTO mutation_requests (actor_id, operation, idempotency_key, request_sha256, response) "
            "VALUES (%s, %s, %s, %s, %s::jsonb)",
            (scoped_actor, operation, key, digest, json.dumps(response)),
        )
        return response


def _audit(connection, actor: Actor, action: str, subject_id: UUID, detail: dict):
    if action not in EVENT_TYPES:
        raise ValueError(f"unregistered outbox event: {action}")
    tenant_id = stable_id(f"tenant/{actor.tenant}")
    connection.execute(
        "INSERT INTO audit_events (id, tenant_id, actor_id, action, subject_id, detail) "
        "VALUES (%s, %s, %s, %s, %s, %s::jsonb)",
        (uuid4(), tenant_id, stable_id(f"account/{actor.account}"), action, subject_id, json.dumps(detail)),
    )
    connection.execute(
        "INSERT INTO outbox_events (id, tenant_id, event_type, payload) "
        "VALUES (%s, %s, %s, %s::jsonb)",
        (uuid4(), tenant_id, action, json.dumps({"subject_id": str(subject_id)})),
    )


def _invalidate_answers(connection, actor: Actor):
    accounts = [item.account for item in ACCOUNTS.values() if item.tenant == actor.tenant]
    connection.execute("DELETE FROM query_requests WHERE tenant_id = %s OR actor_id = ANY(%s::text[])",
                       (stable_id(f"tenant/{actor.tenant}"), accounts))


def _source(row) -> dict:
    return {
        "source_id": str(row[1]), "version_id": str(row[0]), "version": row[2],
        "kind": row[3], "sha256": row[4].strip(), "recorded_at": row[5].isoformat(),
        "status": row[6], "external_label": row[7],
        "valid_from": row[8].isoformat(), "valid_to": row[9].isoformat() if row[9] else None,
        "content": row[10], "origin": row[11], "created_by": row[12],
        "sections": [section.as_dict() for section in parse_sections(row[3], row[10])],
        "permissions": row[13], "superseded_at": row[14].isoformat() if row[14] else None,
        "etag": f'"sv-{row[0]}"',
    }


def _decision(row) -> dict:
    return {
        "decision_id": str(row[1]), "version_id": str(row[0]), "version": row[2],
        "status": row[3], "valid_from": row[4].isoformat(),
        "valid_to": row[5].isoformat() if row[5] else None,
        "recorded_at": row[6].isoformat(), "owner_id": str(row[7]),
        "approver_id": str(row[8]) if row[8] else None,
        "evidence_version_ids": [str(item) for item in row[9]],
        "title": row[10], "supersedes_decision_id": str(row[11]) if row[11] else None,
        "etag": f'"dv-{row[0]}"',
    }


def _validate_evidence(connection, actor: Actor, version_ids: list[UUID], valid_from: date, valid_to: date | None):
    rows = connection.execute(
        "SELECT id, content, content_sha256, valid_from, valid_to FROM source_versions "
        "WHERE tenant_id = %s AND id = ANY(%s::uuid[]) AND %s = ANY(roles) "
        "AND revoked_at IS NULL AND superseded_at IS NULL "
        "AND status IN ('ready', 'recorded', 'corrected_record', 'approved')",
        (stable_id(f"tenant/{actor.tenant}"), version_ids, actor.role),
    ).fetchall()
    if len(rows) != len(version_ids) or any(hashlib.sha256(row[1].encode()).hexdigest() != row[2].strip() for row in rows):
        raise HTTPException(status_code=409, detail="Evidence version is unavailable or no longer current")
    if any(row[3] > valid_from or (row[4] is not None and (valid_to is None or row[4] < valid_to)) for row in rows):
        raise HTTPException(status_code=409, detail="Evidence valid interval does not cover the decision")


def create_source(database_url: str, actor: Actor, body: SourceCreate, key: str) -> dict:
    _require_author(actor)
    if actor.role not in body.permissions:
        raise HTTPException(status_code=422, detail="Source permissions must include its author role")

    def perform(connection):
        source_id, version_id = uuid4(), uuid4()
        label = f"DEMO-{str(source_id)[:8]}-v1"
        digest = hashlib.sha256(body.content.encode("utf-8")).hexdigest()
        row = connection.execute(
            "INSERT INTO source_versions (id, source_id, tenant_id, version, kind, recorded_at, "
            "valid_from, valid_to, status, content_sha256, content, roles, external_label, origin, created_by) "
            "VALUES (%s, %s, %s, 1, %s, now(), %s, %s, 'ready', %s, %s, %s, %s, %s, %s) "
            f"RETURNING {SOURCE_COLUMNS}",
            (version_id, source_id, stable_id(f"tenant/{actor.tenant}"), body.kind,
             body.valid_from, body.valid_to, digest, body.content, body.permissions,
             label, body.origin, actor.account),
        ).fetchone()
        index_source(connection, stable_id(f"tenant/{actor.tenant}"), version_id, body.kind, body.content)
        connection.execute(
            "INSERT INTO ingestion_jobs (id, tenant_id, source_version_id, status) "
            "VALUES (%s, %s, %s, 'ready')",
            (uuid4(), stable_id(f"tenant/{actor.tenant}"), version_id),
        )
        _audit(connection, actor, "source.created", version_id, {"source_id": str(source_id), "sha256": digest})
        return _source(row)

    return _mutation(database_url, actor, "source.create", key, body.model_dump(mode="json"), perform)


def append_source(database_url: str, actor: Actor, source_id: UUID, body: SourceCreate, etag: str, key: str) -> dict:
    _require_author(actor)
    if actor.role not in body.permissions:
        raise HTTPException(status_code=422, detail="Source permissions must include its author role")

    def perform(connection):
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (int.from_bytes(source_id.bytes[:8], "big", signed=True),))
        prior = connection.execute(
            f"SELECT {SOURCE_COLUMNS} FROM source_versions WHERE tenant_id = %s AND source_id = %s "
            "ORDER BY version DESC LIMIT 1 FOR UPDATE",
            (stable_id(f"tenant/{actor.tenant}"), source_id),
        ).fetchone()
        if prior is None:
            raise HTTPException(status_code=404, detail="Source not found")
        if prior[12] != actor.account:
            raise HTTPException(status_code=403, detail="Only the source author can append a version")
        if etag != _source(prior)["etag"]:
            raise HTTPException(status_code=409, detail="Stale source version")
        if prior[14] is not None:
            raise HTTPException(status_code=409, detail="Source version already superseded")
        if prior[15] is not None:
            raise HTTPException(status_code=409, detail="Source is revoked")
        connection.execute("UPDATE source_versions SET superseded_at = now() WHERE id = %s", (prior[0],))
        version_id = uuid4()
        digest = hashlib.sha256(body.content.encode("utf-8")).hexdigest()
        row = connection.execute(
            "INSERT INTO source_versions (id, source_id, tenant_id, version, kind, recorded_at, "
            "valid_from, valid_to, status, content_sha256, content, roles, external_label, origin, created_by) "
            "VALUES (%s, %s, %s, %s, %s, now(), %s, %s, 'ready', %s, %s, %s, %s, %s, %s) "
            f"RETURNING {SOURCE_COLUMNS}",
            (version_id, source_id, stable_id(f"tenant/{actor.tenant}"), prior[2] + 1,
             body.kind, body.valid_from, body.valid_to, digest, body.content, body.permissions,
             f"DEMO-{str(source_id)[:8]}-v{prior[2] + 1}", body.origin, actor.account),
        ).fetchone()
        index_source(connection, stable_id(f"tenant/{actor.tenant}"), version_id, body.kind, body.content)
        connection.execute(
            "INSERT INTO ingestion_jobs (id, tenant_id, source_version_id, status) "
            "VALUES (%s, %s, %s, 'ready')",
            (uuid4(), stable_id(f"tenant/{actor.tenant}"), version_id),
        )
        _audit(connection, actor, "source.versioned", version_id, {"previous_version_id": str(prior[0]), "sha256": digest})
        _invalidate_answers(connection, actor)
        return _source(row)

    request = {"source_id": str(source_id), "if_match": etag, **body.model_dump(mode="json")}
    return _mutation(database_url, actor, "source.append", key, request, perform)


def push_connector_snapshot(database_url: str, actor: Actor, connector_id: str, body: ConnectorSnapshot,
                            key: str, allowed: frozenset[str]) -> dict:
    _require_author(actor)
    if connector_id not in allowed or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", connector_id):
        raise HTTPException(status_code=403, detail="Connector is not enabled")
    source = body.source
    if actor.role not in source.permissions:
        raise HTTPException(status_code=422, detail="Source permissions must include its author role")
    digest = hashlib.sha256(source.content.encode("utf-8")).hexdigest()
    if digest != body.sha256:
        raise HTTPException(status_code=422, detail="Snapshot checksum does not match content")
    tenant_id = stable_id(f"tenant/{actor.tenant}")

    def perform(connection):
        lock_bytes = hashlib.sha256(f"{tenant_id}/{connector_id}/{body.remote_id}".encode()).digest()[:8]
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (int.from_bytes(lock_bytes, "big", signed=True),))
        binding = connection.execute(
            "SELECT source_id, remote_version, source_version_id FROM connector_objects "
            "WHERE tenant_id = %s AND connector_id = %s AND external_id = %s FOR UPDATE",
            (tenant_id, connector_id, body.remote_id),
        ).fetchone()
        seen_revision = connection.execute(
            "SELECT source_version_id FROM connector_revisions WHERE tenant_id = %s "
            "AND connector_id = %s AND external_id = %s AND remote_version = %s",
            (tenant_id, connector_id, body.remote_id, body.remote_version),
        ).fetchone()
        if binding:
            prior = connection.execute(f"SELECT {SOURCE_COLUMNS} FROM source_versions WHERE id = %s FOR UPDATE",
                                       (binding[2],)).fetchone()
            if prior is None or prior[14] is not None or prior[15] is not None:
                raise HTTPException(status_code=409, detail="Connector source changed outside its revision stream")
            if binding[1] == body.remote_version:
                if (prior[4].strip() != digest or prior[3] != source.kind
                        or prior[8] != source.valid_from or prior[9] != source.valid_to
                        or set(prior[13]) != set(source.permissions)):
                    raise HTTPException(status_code=409, detail="Remote version changed without a new revision")
                return _source(prior)
            if seen_revision:
                raise HTTPException(status_code=409, detail="Remote revision was already imported")
            source_id, version, action = binding[0], prior[2] + 1, "source.connector_versioned"
            connection.execute("UPDATE source_versions SET superseded_at = now() WHERE id = %s", (prior[0],))
        else:
            if seen_revision:
                raise HTTPException(status_code=409, detail="Remote revision has no current binding")
            source_id, version, action = uuid4(), 1, "source.connector_created"
        version_id = uuid4()
        row = connection.execute(
            "INSERT INTO source_versions (id, source_id, tenant_id, version, kind, recorded_at, "
            "valid_from, valid_to, status, content_sha256, content, roles, external_label, origin, created_by) "
            "VALUES (%s, %s, %s, %s, %s, now(), %s, %s, 'ready', %s, %s, %s, %s, %s, %s) "
            f"RETURNING {SOURCE_COLUMNS}",
            (version_id, source_id, tenant_id, version, source.kind, source.valid_from, source.valid_to,
             digest, source.content, source.permissions, f"DEMO-{str(source_id)[:8]}-v{version}",
             f"connector:{connector_id}/{body.remote_id}", actor.account),
        ).fetchone()
        index_source(connection, tenant_id, version_id, source.kind, source.content)
        connection.execute("INSERT INTO ingestion_jobs (id, tenant_id, source_version_id, status) "
                           "VALUES (%s, %s, %s, 'ready')", (uuid4(), tenant_id, version_id))
        if binding:
            connection.execute("UPDATE connector_objects SET remote_version = %s, source_version_id = %s "
                               "WHERE tenant_id = %s AND connector_id = %s AND external_id = %s",
                               (body.remote_version, version_id, tenant_id, connector_id, body.remote_id))
            _invalidate_answers(connection, actor)
        else:
            connection.execute("INSERT INTO connector_objects (tenant_id, connector_id, external_id, "
                               "source_id, remote_version, source_version_id) VALUES (%s, %s, %s, %s, %s, %s)",
                               (tenant_id, connector_id, body.remote_id, source_id, body.remote_version, version_id))
        connection.execute("INSERT INTO connector_revisions (tenant_id, connector_id, external_id, remote_version, source_version_id) "
                           "VALUES (%s, %s, %s, %s, %s)",
                           (tenant_id, connector_id, body.remote_id, body.remote_version, version_id))
        _audit(connection, actor, action, version_id, {"connector_id": connector_id, "remote_id": body.remote_id,
                                                      "remote_version": body.remote_version, "sha256": digest})
        return _source(row)

    return _mutation(database_url, actor, "connector.push", key,
                     {"connector_id": connector_id, **body.model_dump(mode="json")}, perform)


def list_sources(database_url: str, actor: Actor) -> list[dict]:
    with connect(database_url) as connection:
        rows = connection.execute(
            f"SELECT DISTINCT ON (source_id) {SOURCE_COLUMNS} FROM source_versions "
            "WHERE tenant_id = %s AND created_by IS NOT NULL AND %s = ANY(roles) "
            "AND revoked_at IS NULL ORDER BY source_id, version DESC",
            (stable_id(f"tenant/{actor.tenant}"), actor.role),
        ).fetchall()
    return [_source(row) for row in rows]


def source_history(database_url: str, actor: Actor, source_id: UUID) -> list[dict]:
    with connect(database_url) as connection:
        rows = connection.execute(
            f"SELECT {SOURCE_COLUMNS} FROM source_versions WHERE tenant_id = %s AND source_id = %s "
            "AND created_by IS NOT NULL AND %s = ANY(roles) AND revoked_at IS NULL ORDER BY version",
            (stable_id(f"tenant/{actor.tenant}"), source_id, actor.role),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")
    return [_source(row) for row in rows]


def revoke_source(database_url: str, actor: Actor, source_id: UUID, body: SourceRevocation,
                  etag: str, key: str) -> dict:
    """Retire every version of one authored source from all API evidence paths."""
    _require_author(actor)
    tenant_id = stable_id(f"tenant/{actor.tenant}")

    def perform(connection):
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (int.from_bytes(source_id.bytes[:8], "big", signed=True),))
        latest = connection.execute(
            f"SELECT {SOURCE_COLUMNS} FROM source_versions WHERE tenant_id = %s AND source_id = %s "
            "ORDER BY version DESC LIMIT 1 FOR UPDATE", (tenant_id, source_id),
        ).fetchone()
        if latest is None or latest[12] is None:
            raise HTTPException(status_code=404, detail="Source not found")
        if latest[12] != actor.account:
            raise HTTPException(status_code=403, detail="Only the source author can revoke it")
        if latest[15] is not None:
            raise HTTPException(status_code=409, detail="Source is already revoked")
        if etag != _source(latest)["etag"]:
            raise HTTPException(status_code=409, detail="Stale source version")
        versions = connection.execute(
            "UPDATE source_versions SET revoked_at = now() WHERE tenant_id = %s AND source_id = %s "
            "AND revoked_at IS NULL RETURNING id", (tenant_id, source_id),
        ).fetchall()
        version_ids = [row[0] for row in versions]
        connection.execute("DELETE FROM source_chunks WHERE tenant_id = %s AND source_version_id = ANY(%s::uuid[])",
                           (tenant_id, version_ids))
        # Preserve retry keys while removing source text from previously stored mutation responses.
        connection.execute(
            "UPDATE mutation_requests SET response = %s::jsonb WHERE response->>'source_id' = %s "
            "AND operation IN ('source.create', 'source.append', 'connector.push')",
            (json.dumps({"source_id": str(source_id), "status": "revoked"}), str(source_id)),
        )
        connection.execute(
            "UPDATE mutation_requests SET response = jsonb_build_object("
            "'decision_id', response->>'decision_id', 'status', 'evidence_revoked') "
            "WHERE response->>'decision_id' IN (SELECT DISTINCT decision_id::text FROM decision_versions "
            "WHERE tenant_id = %s AND evidence_version_ids && %s::uuid[]) "
            "AND operation IN ('decision.create', 'decision.review')",
            (tenant_id, version_ids),
        )
        _invalidate_answers(connection, actor)
        _audit(connection, actor, "source.revoked", latest[0],
               {"source_id": str(source_id), "version_ids": [str(item) for item in version_ids],
                "reason": body.reason})
        return {"source_id": str(source_id), "revoked_version_ids": [str(item) for item in version_ids],
                "status": "revoked"}

    return _mutation(database_url, actor, "source.revoke", key,
                     {"source_id": str(source_id), "if_match": etag, **body.model_dump(mode="json")}, perform)


def create_decision(database_url: str, actor: Actor, body: DecisionDraft, key: str) -> dict:
    _require_author(actor)

    def perform(connection):
        if body.supersedes_decision_id is not None:
            prior = connection.execute(
                "SELECT 1 FROM decision_versions WHERE tenant_id = %s AND decision_id = %s "
                "AND status = 'approved' LIMIT 1",
                (stable_id(f"tenant/{actor.tenant}"), body.supersedes_decision_id),
            ).fetchone()
            if prior is None:
                raise HTTPException(status_code=409, detail="Superseded decision is not approved in this tenant")
        _validate_evidence(connection, actor, body.evidence_version_ids, body.valid_from, body.valid_to)
        decision_id, version_id = uuid4(), uuid4()
        row = connection.execute(
            "INSERT INTO decision_versions (id, decision_id, tenant_id, version, status, valid_from, "
            "valid_to, recorded_at, owner_id, evidence_version_ids, title, supersedes_decision_id) "
            "VALUES (%s, %s, %s, 1, 'draft', %s, %s, now(), %s, %s, %s, %s) "
            f"RETURNING {DECISION_COLUMNS}",
            (version_id, decision_id, stable_id(f"tenant/{actor.tenant}"), body.valid_from,
             body.valid_to, stable_id(f"account/{actor.account}"), body.evidence_version_ids,
             body.title, body.supersedes_decision_id),
        ).fetchone()
        _audit(connection, actor, "decision.drafted", version_id, {"decision_id": str(decision_id)})
        return _decision(row)

    return _mutation(database_url, actor, "decision.create", key, body.model_dump(mode="json"), perform)


def review_decision(database_url: str, actor: Actor, decision_id: UUID, body: ReviewAction, etag: str, key: str) -> dict:
    _require_reviewer(actor)

    def perform(connection):
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (int.from_bytes(decision_id.bytes[:8], "big", signed=True),))
        prior = connection.execute(
            f"SELECT {DECISION_COLUMNS} FROM decision_versions WHERE tenant_id = %s AND decision_id = %s "
            "ORDER BY version DESC LIMIT 1 FOR UPDATE",
            (stable_id(f"tenant/{actor.tenant}"), decision_id),
        ).fetchone()
        if prior is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        if not _can_read_evidence(connection, actor, prior[9]):
            raise HTTPException(status_code=404, detail="Decision not found")
        if etag != _decision(prior)["etag"] or prior[3] not in ("draft", "in_review"):
            raise HTTPException(status_code=409, detail="Stale or already reviewed decision")
        if prior[7] == stable_id(f"account/{actor.account}"):
            raise HTTPException(status_code=409, detail="A decision author cannot approve or reject their own draft")
        if body.action == "approve":
            _validate_evidence(connection, actor, prior[9], prior[4], prior[5])
        version_id = uuid4()
        row = connection.execute(
            "INSERT INTO decision_versions (id, decision_id, tenant_id, version, status, valid_from, "
            "valid_to, recorded_at, owner_id, approver_id, evidence_version_ids, title, supersedes_decision_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s, %s, %s, %s, %s) "
            f"RETURNING {DECISION_COLUMNS}",
            (version_id, decision_id, stable_id(f"tenant/{actor.tenant}"), prior[2] + 1,
             "approved" if body.action == "approve" else "rejected", prior[4], prior[5],
             prior[7], stable_id(f"account/{actor.account}"), prior[9], prior[10], prior[11]),
        ).fetchone()
        _audit(connection, actor, "decision.reviewed", version_id, {"action": body.action, "reason": body.reason or ""})
        if body.action == "approve":
            _invalidate_answers(connection, actor)
        return _decision(row)

    request = {"decision_id": str(decision_id), "if_match": etag, **body.model_dump(mode="json")}
    return _mutation(database_url, actor, "decision.review", key, request, perform)


def list_decisions(database_url: str, actor: Actor) -> list[dict]:
    if actor.role not in ("owner", "auditor"):
        raise HTTPException(status_code=403, detail="Decision review history is restricted")
    with connect(database_url) as connection:
        rows = connection.execute(
            f"SELECT DISTINCT ON (decision_id) {DECISION_COLUMNS} FROM decision_versions "
            "WHERE tenant_id = %s ORDER BY decision_id, version DESC",
            (stable_id(f"tenant/{actor.tenant}"),),
        ).fetchall()
        return [_decision(row) for row in rows if _can_read_evidence(connection, actor, row[9])]


def _can_read_evidence(connection, actor: Actor, version_ids) -> bool:
    count = connection.execute(
        "SELECT count(*) FROM source_versions WHERE tenant_id = %s AND id = ANY(%s::uuid[]) "
        "AND %s = ANY(roles) AND revoked_at IS NULL",
        (stable_id(f"tenant/{actor.tenant}"), version_ids, actor.role),
    ).fetchone()[0]
    return count == len(version_ids)


def decision_history(database_url: str, actor: Actor, decision_id: UUID) -> list[dict]:
    if actor.role not in ("owner", "auditor"):
        raise HTTPException(status_code=403, detail="Decision review history is restricted")
    with connect(database_url) as connection:
        rows = connection.execute(
            f"SELECT {DECISION_COLUMNS} FROM decision_versions WHERE tenant_id = %s "
            "AND decision_id = %s ORDER BY version",
            (stable_id(f"tenant/{actor.tenant}"), decision_id),
        ).fetchall()
        rows = [row for row in rows if _can_read_evidence(connection, actor, row[9])]
    if not rows:
        raise HTTPException(status_code=404, detail="Decision not found")
    return [_decision(row) for row in rows]
