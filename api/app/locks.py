"""Shared tenant-level ordering for evidence reads and protected mutations."""

import hashlib

from .auth import Actor


def evidence_lock_key(actor: Actor) -> int:
    raw = hashlib.sha256(f"decisiontrace/evidence/{actor.tenant}".encode()).digest()[:8]
    return int.from_bytes(raw, "big", signed=True)
