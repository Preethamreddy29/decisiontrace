"""Versioned contract for events handled by the local outbox worker."""

from uuid import UUID


EVENT_VERSION = 1
EVENT_TYPES = frozenset({
    "foundation.ping",
    "source.created",
    "source.versioned",
    "source.connector_created",
    "source.connector_versioned",
    "source.revoked",
    "decision.drafted",
    "decision.reviewed",
    "change_watch.created",
    "change_watch.reviewed",
})


def valid_event(event_type: str, event_version: int, payload: object) -> bool:
    if event_type not in EVENT_TYPES or event_version != EVENT_VERSION or not isinstance(payload, dict):
        return False
    if event_type == "foundation.ping":
        return payload == {}
    if set(payload) != {"subject_id"}:
        return False
    try:
        UUID(payload["subject_id"])
    except (TypeError, ValueError, AttributeError):
        return False
    return True
