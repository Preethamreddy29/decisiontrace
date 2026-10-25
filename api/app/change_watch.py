"""Reviewable downstream source changes bound to approved decision evidence."""

import hashlib
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row

from .auth import Actor
from .db import connect
from .seed import stable_id
from .workflow import _audit, _can_read_evidence, _mutation, _require_author, _require_reviewer


class WatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_evidence_version_id: UUID
    downstream_source_id: UUID
    relation_type: Literal["implements", "tests", "measures"]


class WatchReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_source_version_id: UUID
    outcome: Literal["drift", "aligned"]
    reason: str = Field(min_length=8, max_length=1000)


def _tenant(actor: Actor) -> UUID:
    return stable_id(f"tenant/{actor.tenant}")


def create_watch(database_url: str, actor: Actor, decision_id: UUID, body: WatchCreate, key: str) -> dict:
    _require_author(actor)

    def perform(connection):
        decision = connection.execute(
            "SELECT id, status, evidence_version_ids FROM decision_versions "
            "WHERE tenant_id = %s AND decision_id = %s ORDER BY version DESC LIMIT 1",
            (_tenant(actor), decision_id),
        ).fetchone()
        if decision is None or not _can_read_evidence(connection, actor, decision[2]):
            raise HTTPException(status_code=404, detail="Decision not found")
        if decision[1] != "approved" or body.decision_evidence_version_id not in decision[2]:
            raise HTTPException(status_code=409, detail="Choose evidence from the current approved decision")
        downstream = connection.execute(
            "SELECT id FROM source_versions WHERE tenant_id = %s AND source_id = %s "
            "AND %s = ANY(roles) AND revoked_at IS NULL ORDER BY version DESC LIMIT 1",
            (_tenant(actor), body.downstream_source_id, actor.role),
        ).fetchone()
        if downstream is None:
            raise HTTPException(status_code=404, detail="Downstream source not found")
        existing = connection.execute(
            "SELECT 1 FROM change_watches WHERE tenant_id = %s AND decision_version_id = %s "
            "AND downstream_source_id = %s AND relation_type = %s",
            (_tenant(actor), decision[0], body.downstream_source_id, body.relation_type),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="This decision and source are already linked")
        watch_id = uuid4()
        connection.execute(
            "INSERT INTO change_watches (id, tenant_id, decision_version_id, decision_evidence_version_id, "
            "downstream_source_id, baseline_source_version_id, relation_type, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (watch_id, _tenant(actor), decision[0], body.decision_evidence_version_id,
             body.downstream_source_id, downstream[0], body.relation_type, actor.account),
        )
        _audit(connection, actor, "change_watch.created", watch_id,
               {"decision_version_id": str(decision[0]), "baseline_source_version_id": str(downstream[0])})
        return {"watch_id": str(watch_id), "decision_version_id": str(decision[0]),
                "baseline_source_version_id": str(downstream[0]), "relation_type": body.relation_type}

    return _mutation(database_url, actor, "change_watch.create", key,
                     {"decision_id": str(decision_id), **body.model_dump(mode="json")}, perform)


def list_watches(database_url: str, actor: Actor) -> list[dict]:
    if actor.role not in ("owner", "auditor"):
        raise HTTPException(status_code=403, detail="Change watches are restricted")
    with connect(database_url) as connection:
        connection.row_factory = dict_row
        rows = connection.execute(
            "SELECT w.id AS watch_id, w.decision_version_id, w.decision_evidence_version_id, "
            "w.downstream_source_id, w.baseline_source_version_id, w.relation_type, w.created_by, "
            "d.title AS decision_title, e.source_id AS evidence_source_id, e.external_label AS evidence_label, "
            "e.content AS evidence_content, e.content_sha256 AS evidence_sha256, "
            "b.external_label AS baseline_label, b.content AS baseline_content, "
            "b.content_sha256 AS baseline_sha256, "
            "s.id AS observed_version_id, s.external_label AS observed_label, s.content AS observed_content, "
            "s.content_sha256 AS observed_sha256, r.outcome, r.reason, r.reviewed_by, r.reviewed_at "
            "FROM change_watches w "
            "JOIN decision_versions d ON d.id = w.decision_version_id AND d.tenant_id = w.tenant_id "
            "JOIN source_versions e ON e.id = w.decision_evidence_version_id AND e.tenant_id = w.tenant_id "
            "JOIN source_versions b ON b.id = w.baseline_source_version_id AND b.tenant_id = w.tenant_id "
            "JOIN LATERAL (SELECT id, external_label, content, content_sha256, roles FROM source_versions "
            "WHERE tenant_id = w.tenant_id AND source_id = w.downstream_source_id AND revoked_at IS NULL "
            "ORDER BY version DESC LIMIT 1) s ON true "
            "LEFT JOIN change_watch_reviews r ON r.watch_id = w.id AND r.observed_source_version_id = s.id "
            "WHERE w.tenant_id = %s AND e.revoked_at IS NULL AND b.revoked_at IS NULL "
            "AND %s = ANY(e.roles) AND %s = ANY(b.roles) AND %s = ANY(s.roles) "
            "ORDER BY w.created_at DESC LIMIT 100",
            (_tenant(actor), actor.role, actor.role, actor.role),
        ).fetchall()
    result = []
    for row in rows:
        if (hashlib.sha256(row["evidence_content"].encode()).hexdigest() != row["evidence_sha256"].strip()
                or hashlib.sha256(row["baseline_content"].encode()).hexdigest() != row["baseline_sha256"].strip()
                or hashlib.sha256(row["observed_content"].encode()).hexdigest() != row["observed_sha256"].strip()):
            continue
        changed = row["observed_version_id"] != row["baseline_source_version_id"]
        result.append({
            "watch_id": str(row["watch_id"]), "decision_version_id": str(row["decision_version_id"]),
            "decision_title": row["decision_title"], "relation_type": row["relation_type"],
            "created_by": row["created_by"], "decision_evidence": {
                "source_id": str(row["evidence_source_id"]),
                "version_id": str(row["decision_evidence_version_id"]),
                "label": row["evidence_label"], "content": row["evidence_content"]},
            "downstream": {"source_id": str(row["downstream_source_id"]),
                           "baseline_version_id": str(row["baseline_source_version_id"]),
                           "baseline_label": row["baseline_label"],
                           "baseline_content": row["baseline_content"],
                           "observed_version_id": str(row["observed_version_id"]),
                           "observed_label": row["observed_label"], "observed_content": row["observed_content"]},
            "status": (row["outcome"] if row["outcome"] else "needs_review" if changed else "current"),
            "review": ({"reason": row["reason"], "reviewed_by": row["reviewed_by"],
                        "reviewed_at": row["reviewed_at"].isoformat()} if row["outcome"] else None),
        })
    return result


def review_watch(database_url: str, actor: Actor, watch_id: UUID, body: WatchReview, key: str) -> dict:
    _require_reviewer(actor)

    def perform(connection):
        watch = connection.execute(
            "SELECT created_by, baseline_source_version_id, downstream_source_id, decision_evidence_version_id "
            "FROM change_watches WHERE tenant_id = %s AND id = %s FOR UPDATE", (_tenant(actor), watch_id),
        ).fetchone()
        if watch is None:
            raise HTTPException(status_code=404, detail="Change watch not found")
        if watch[0] == actor.account:
            raise HTTPException(status_code=409, detail="A watch creator cannot review their own finding")
        visible = next((item for item in list_watches(database_url, actor) if item["watch_id"] == str(watch_id)), None)
        if visible is None:
            raise HTTPException(status_code=404, detail="Change watch not found")
        if visible["status"] != "needs_review" or visible["downstream"]["observed_version_id"] != str(body.observed_source_version_id):
            raise HTTPException(status_code=409, detail="Finding is stale or already reviewed")
        connection.execute(
            "INSERT INTO change_watch_reviews (id, watch_id, observed_source_version_id, outcome, reason, reviewed_by) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (uuid4(), watch_id, body.observed_source_version_id, body.outcome, body.reason, actor.account),
        )
        _audit(connection, actor, "change_watch.reviewed", watch_id,
               {"observed_version_id": str(body.observed_source_version_id), "outcome": body.outcome})
        return {"watch_id": str(watch_id), "observed_source_version_id": str(body.observed_source_version_id),
                "status": body.outcome, "reason": body.reason}

    return _mutation(database_url, actor, "change_watch.review", key,
                     {"watch_id": str(watch_id), **body.model_dump(mode="json")}, perform)
