"""Pinned, deterministic token-set vector baseline for retrieval plumbing.

This is a reproducible local baseline, not a semantic model. A later model
adapter must use a different profile and rebuild all indexed vectors.
"""

import hashlib
import re


PROFILE = "token-set-sha256-64-v1"
DIMENSIONS = 64
_TOKEN = re.compile(r"[a-z0-9]+")


def vector_literal(text: str) -> str | None:
    """Return a pgvector literal with exact binary components, or None."""
    positions = {
        int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big") % DIMENSIONS
        for token in _TOKEN.findall(text.casefold())
    }
    if not positions:
        return None
    return "[" + ",".join("1" if index in positions else "0" for index in range(DIMENSIONS)) + "]"


def vector_checksum(literal: str) -> str:
    return hashlib.sha256(literal.encode("ascii")).hexdigest()
