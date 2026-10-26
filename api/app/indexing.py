"""Bounded, checksummed section chunks stored with their source version."""

import hashlib
from dataclasses import dataclass
from uuid import UUID

from .sections import parse_sections


CHUNKER_VERSION = "section-text-v1"
MAX_CHARS = 1200


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    section_id: str
    start_char: int
    end_char: int
    sha256: str
    content_text: str


def chunk_source(kind: str, content: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for section in parse_sections(kind, content):
        position = section.start_char
        while position < section.end_char:
            limit = min(position + MAX_CHARS, section.end_char)
            cut = limit
            if limit < section.end_char:
                whitespace = max(content.rfind("\n", position + 400, limit),
                                 content.rfind(" ", position + 400, limit))
                if whitespace > position:
                    cut = whitespace + 1
            start, end = position, cut
            while start < end and content[start].isspace():
                start += 1
            while end > start and content[end - 1].isspace():
                end -= 1
            if start < end:
                passage = content[start:end]
                digest = hashlib.sha256(passage.encode("utf-8")).hexdigest()
                base = hashlib.sha256(f"{CHUNKER_VERSION}\0{section.section_id}\0{digest}".encode()).hexdigest()[:24]
                seen[base] = seen.get(base, 0) + 1
                chunk_id = base + (f"~{seen[base]}" if seen[base] > 1 else "")
                chunks.append(Chunk(chunk_id, section.section_id, start, end, digest, passage))
            position = cut
    return chunks


def index_source(connection, tenant_id: UUID, version_id: UUID, kind: str, content: str) -> int:
    connection.execute("DELETE FROM source_chunks WHERE tenant_id = %s AND source_version_id = %s", (tenant_id, version_id))
    chunks = chunk_source(kind, content)
    for item in chunks:
        connection.execute(
            "INSERT INTO source_chunks (tenant_id, source_version_id, chunk_id, section_id, "
            "start_char, end_char, content_sha256, chunker_version, content_text) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (tenant_id, version_id, item.chunk_id, item.section_id,
             item.start_char, item.end_char, item.sha256, CHUNKER_VERSION, item.content_text),
        )
    return len(chunks)
