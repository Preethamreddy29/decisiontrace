"""Fail-closed verification for the bounded exact-quotation answer path.

This proves citation identity and exact quotation, not semantic entailment for
arbitrary generated claims. A future generator needs a separately evaluated
support check before its outputs can use this gate.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from .auth import Actor
from .db import connect
from .sections import section_for_span
from .seed import stable_id

if TYPE_CHECKING:
    from .query import QueryRequest


VERSION = "exact-authorized-quote-v1"
_SOURCE_KINDS_REQUIRING_REVIEW = frozenset({"markdown", "transcript", "json"})


def verify_answer(database_url: str, actor: Actor, request: QueryRequest, answer: object) -> bool:
    """Return true only when every displayed claim has current exact evidence."""
    from .query import visible_sources

    if not isinstance(answer, dict):
        return False
    valid_on = request.valid_on or request.recorded_as_of.date()
    if answer.get("valid_on") != valid_on.isoformat():
        return False
    try:
        recorded_as_of = datetime.fromisoformat(answer["recorded_as_of"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    if recorded_as_of != request.recorded_as_of:
        return False

    status, claims = answer.get("status"), answer.get("claims")
    if status not in {"answered", "conflict", "abstain", "denied"} or not isinstance(claims, list):
        return False
    if status in {"abstain", "denied"}:
        return not claims
    if not claims:
        return False

    visible = {
        source.version_id: source
        for source in visible_sources(database_url, actor, request.recorded_as_of, request.source_ids)
    }
    tenant_id = stable_id(f"tenant/{actor.tenant}")
    with connect(database_url) as connection:
        for claim in claims:
            if not isinstance(claim, dict):
                return False
            citations = claim.get("citations")
            if not isinstance(citations, list) or len(citations) != 1:
                return False
            citation = citations[0]
            if not isinstance(citation, dict):
                return False
            quote = citation.get("quote")
            if not isinstance(quote, str) or not quote or claim.get("text") != quote:
                return False
            source = visible.get(citation.get("version_id"))
            if source is None or citation.get("source_id") != source.source_id:
                return False
            if citation.get("label") != source.label:
                return False
            if source.valid_from > valid_on or (source.valid_to is not None and valid_on >= source.valid_to):
                return False
            start, end = citation.get("start_char"), citation.get("end_char")
            if type(start) is not int or type(end) is not int or start < 0 or end <= start:
                return False
            if end > len(source.content) or source.content[start:end] != quote:
                return False
            try:
                section = section_for_span(source.kind, source.content, start, end)
            except ValueError:
                return False
            if citation.get("section_id") != section.section_id:
                return False

            decision_version_id = claim.get("decision_version_id")
            if status == "answered" and source.kind in _SOURCE_KINDS_REQUIRING_REVIEW and not decision_version_id:
                return False
            if decision_version_id is None:
                continue
            try:
                decision_id = UUID(decision_version_id)
            except (TypeError, ValueError, AttributeError):
                return False
            decision = connection.execute(
                "SELECT status, valid_from, valid_to, recorded_at, evidence_version_ids "
                "FROM decision_versions WHERE tenant_id = %s AND id = %s",
                (tenant_id, decision_id),
            ).fetchone()
            if decision is None or decision[0] != "approved":
                return False
            if decision[1] > valid_on or (decision[2] is not None and valid_on >= decision[2]):
                return False
            if decision[3] > request.recorded_as_of:
                return False
            evidence_ids = {str(item) for item in decision[4]}
            if source.version_id not in evidence_ids or not evidence_ids.issubset(visible):
                return False
    return True
