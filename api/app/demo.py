"""Deterministic, synthetic-only historical policy demo.

This is deliberately separate from the planned authenticated /v1 API. The caller
selects a fictional tenant and role for demonstration; no security claim follows
from that selection.
"""

import json
import hashlib
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .db import connect
from .seed import stable_id


CORPUS_PATH = Path(__file__).resolve().parents[2] / "corpus" / "sources.json"
CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
LABELS = {str(stable_id(f"version/{item['id']}")): item for item in CORPUS["sources"]}


class DemoQuery(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    tenant: Literal["cedar", "lumen"] = "cedar"
    role: Literal["owner", "engineer", "qa", "auditor", "viewer"] = "auditor"
    valid_on: date
    recorded_as_of: datetime

    @field_validator("recorded_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_as_of must include a timezone")
        return value.astimezone(timezone.utc)


def visible_sources(database_url: str, query: DemoQuery) -> dict[str, dict]:
    """Filter at storage before any question logic or response construction."""
    with connect(database_url) as connection:
        rows = connection.execute(
            "SELECT id, source_id, version, kind, recorded_at, valid_from, valid_to, "
            "status, content, revoked_at, superseded_at, content_sha256 FROM source_versions "
            "WHERE tenant_id = %s AND %s = ANY(roles) AND recorded_at <= %s "
            "AND (revoked_at IS NULL OR revoked_at > %s) "
            "AND (superseded_at IS NULL OR superseded_at > %s)",
            (
                stable_id(f"tenant/{query.tenant}"), query.role,
                query.recorded_as_of, query.recorded_as_of, query.recorded_as_of,
            ),
        ).fetchall()
    result = {}
    for row in rows:
        label = LABELS.get(str(row[0]))
        if label is None:
            continue  # The curated demo never interprets arbitrary unreviewed input.
        if hashlib.sha256(row[8].encode("utf-8")).hexdigest() != row[11].strip():
            continue  # A corrupted stored version cannot support a claim.
        if row[8] != label["text"]:
            continue  # Curated answers are valid only for the frozen fixture text.
        result[label["id"]] = {
            "label": label["id"], "source_id": str(row[1]), "version_id": str(row[0]),
            "version": row[2], "kind": row[3], "recorded_at": row[4].isoformat(),
            "valid_from": row[5].isoformat(),
            "valid_to": row[6].isoformat() if row[6] else None,
            "status": row[7], "text": row[8], "metadata": label,
        }
    return result


def cite(sources: dict[str, dict], *labels: str) -> list[dict]:
    citations = []
    for label in labels:
        source = sources.get(label)
        if source is None:
            return []
        citations.append({key: source[key] for key in (
            "label", "source_id", "version_id", "version", "kind",
            "recorded_at", "valid_from", "valid_to", "status", "text",
        )})
    return citations


def answer(database_url: str, query: DemoQuery) -> dict:
    sources = visible_sources(database_url, query)
    question = re.sub(r"[^a-z0-9]+", " ", query.question.lower()).strip()
    status, message, citations = "abstain", "No permitted evidence supports an answer to this question.", []

    # Tenant and role are scenario controls, not authentication. Never consult
    # another tenant's rows while evaluating a scenario.
    if query.tenant == "cedar" and "lumen" in question and query.role == "viewer":
        status, message = "denied", "No Lumen information may be disclosed in this Cedar-only scenario."
    elif query.tenant == "cedar" and "lumen" in question and "covered" in question:
        citations = cite(sources, "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "No. The Cedar decision is scoped to Cedar."
    elif query.tenant == "lumen" and "policy" in question:
        citations = cite(sources, "SRC-ADR-002-v1")
        if citations:
            status, message = "answered", "Lumen manual overrides require one reviewer and a recorded justification."
    elif "undocumented exception" in question or "why was" in question:
        status, message = "abstain", "No permitted evidence establishes why an undocumented exception was allowed."
    elif "revoked source" in question:
        status, message = "abstain", "A revoked source cannot support an answer after revocation."
    elif "ignore tenant policy" in question or "source says to ignore" in question:
        citations = cite(sources, "SRC-ATTACK-001-v1")
        if citations:
            status, message = "answered", "No. Source text is untrusted data and cannot change tenant authorization rules."
    elif "unresolved contradiction" in question:
        citations = cite(sources, "SRC-DRAFT-001-v1", "SRC-ADR-003-v1")
        if citations:
            status, message = "conflict", "An unapproved draft says overrides stay enabled after 20 May; approved DEC-CEDAR-002 disables them."
    elif "conflicting draft" in question:
        citations = cite(sources, "SRC-DRAFT-001-v1", "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "No. The draft conflicts with approved DEC-CEDAR-002 but has no approval authority."
    elif "implementation test" in question and "change" in question:
        citations = cite(sources, "SRC-TEST-001-v1", "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "No. The active test still expects the old override behavior, creating drift."
    elif "active test" in question and "old behavior" in question:
        citations = cite(sources, "SRC-TEST-001-v1", "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "SRC-TEST-001 version 1 still expects old behavior."
    elif "who approved" in question:
        citations = cite(sources, "SRC-ADR-003-v1")
        if citations:
            approver = sources["SRC-ADR-003-v1"]["metadata"].get("approver")
            if approver:
                status, message = "answered", f"The fictional {approver} approved the superseding decision."
    elif "which source" in question and "superseding decision" in question:
        citations = cite(sources, "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "SRC-ADR-003 version 1 records approval of the superseding decision."
    elif "which source" in question and "correction" in question:
        citations = cite(sources, "SRC-MEETING-001-v2")
        if citations:
            status, message = "answered", "SRC-MEETING-001 version 2 records the correction."
    elif "which sources" in question and "original decision" in question:
        citations = cite(sources, "SRC-MEETING-001-v2", "SRC-ADR-001-v1")
        if citations:
            status, message = "answered", "The corrected meeting record and approved DEC-CEDAR-001 record support the original decision."
    elif "assumption expired" in question or ("assumption" in question and "expired" in question):
        citations = cite(sources, "SRC-ADR-001-v1")
        if citations:
            status, message = "answered", "Yes. ASM-CEDAR-001 had a 1 June review date, and no renewal is recorded in this corpus."
    elif "assumption" in question and "original decision" in question:
        citations = cite(sources, "SRC-ADR-001-v1")
        if citations:
            status, message = "answered", "ASM-CEDAR-001 assumed exception volume would stay low."
    elif "which approved decision superseded" in question:
        citations = cite(sources, "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "DEC-CEDAR-002 superseded DEC-CEDAR-001."
    elif "new policy become effective" in question:
        citations = cite(sources, "SRC-ADR-003-v1")
        if citations:
            status, message = "answered", "The new policy became effective on 20 May 2026."
    elif any(term in question for term in ("correction", "corrected")) and ("when" in question or "known" in question):
        citations = cite(sources, "SRC-MEETING-001-v2")
        if citations:
            status, message = "answered", "The corrected meeting record became known on 12 May 2026 at 11:00 UTC."
    elif "correction" in question and ("new" in question or "create" in question):
        citations = cite(sources, "SRC-MEETING-001-v2", "SRC-ADR-001-v1")
        if citations:
            status, message = "answered", "No. The correction repaired the record of the 30 April decision; it did not adopt a new policy."
    elif any(term in question for term in ("manual override", "manual overrides", "current approved policy", "what applied", "what did decisiontrace know")) and query.tenant == "cedar":
        effective = date(2026, 5, 20)
        if query.valid_on >= effective:
            citations = cite(sources, "SRC-ADR-003-v1")
            if citations:
                status, message = "answered", "Cedar manual overrides are disabled; exceptions use the standard review queue."
        else:
            citations = cite(sources, "SRC-ADR-001-v1")
            if citations and query.valid_on >= date(2026, 5, 1):
                status, message = "answered", "Cedar manual overrides require two independent reviewers and a cap of 10000 minor currency units."
                corrected = cite(sources, "SRC-MEETING-001-v2")
                if corrected:
                    citations = corrected + citations
            else:
                citations = cite(sources, "SRC-MEETING-001-v1")
                if citations and query.valid_on >= date(2026, 5, 1):
                    status, message = "answered", "The then-recorded meeting transcript said one reviewer and a cap of 10000 minor currency units."

    if status == "abstain":
        citations = []
    return {
        "status": status, "answer": message, "citations": citations,
        "tenant": query.tenant, "role": query.role,
        "valid_on": query.valid_on.isoformat(),
        "recorded_as_of": query.recorded_as_of.isoformat(),
        "corpus_version": CORPUS["corpus_version"],
        "mode": "curated_synthetic_demo",
    }
