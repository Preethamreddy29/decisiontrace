"""Deterministic, source-version-local sections with exact content offsets."""

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    start_char: int
    end_char: int

    def as_dict(self) -> dict:
        return {
            "section_id": self.section_id, "title": self.title,
            "start_char": self.start_char, "end_char": self.end_char,
        }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "section"


def _markdown(content: str) -> list[Section]:
    headings = list(re.finditer(r"(?m)^([ \t]{0,3})(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*(?:\r?\n|$)", content))
    if not headings:
        return [Section("body", "Body", 0, len(content))]
    result: list[Section] = []
    if headings[0].start() > 0:
        result.append(Section("body", "Introduction", 0, headings[0].start()))
    path: list[str] = []
    counts: dict[str, int] = {}
    for index, match in enumerate(headings):
        level = len(match.group(2))
        path = path[:level - 1]
        title = match.group(3).strip()
        path.append(_slug(title))
        raw_id = "/".join(path)
        counts[raw_id] = counts.get(raw_id, 0) + 1
        if counts[raw_id] > 1:
            path[-1] += f"~{counts[raw_id]}"
        section_id = "md/" + "/".join(path)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        result.append(Section(section_id, title, match.start(), end))
    return result


def _transcript(content: str) -> list[Section]:
    turns = list(re.finditer(r"(?m)^(?:\[(\d\d:\d\d(?::\d\d)?)\][ \t]*)?([A-Za-z][A-Za-z0-9 _-]{0,60}):[ \t]*", content))
    if not turns:
        return [Section("body", "Transcript", 0, len(content))]
    result: list[Section] = []
    if turns[0].start() > 0:
        result.append(Section("body", "Introduction", 0, turns[0].start()))
    counts: dict[str, int] = {}
    used: dict[str, int] = {}
    for index, match in enumerate(turns):
        speaker = match.group(2).strip()
        key = f"turn/{_slug(speaker)}"
        counts[key] = counts.get(key, 0) + 1
        # A timestamp remains stable when unrelated turns are inserted.
        suffix = match.group(1) or str(counts[key])
        raw_id = f"{key}/{suffix}"
        used[raw_id] = used.get(raw_id, 0) + 1
        section_id = raw_id + (f"~{used[raw_id]}" if used[raw_id] > 1 else "")
        end = turns[index + 1].start() if index + 1 < len(turns) else len(content)
        result.append(Section(section_id, f"{speaker} · {suffix}", match.start(), end))
    return result


def _json(content: str) -> list[Section]:
    decoder = json.JSONDecoder()
    result: list[Section] = []

    def space(position: int) -> int:
        while position < len(content) and content[position].isspace():
            position += 1
        return position

    def walk(position: int, path: list[str]) -> int:
        position = space(position)
        if content[position] == "{":
            position = space(position + 1)
            while content[position] != "}":
                key, position = decoder.raw_decode(content, position)
                position = space(position)
                if content[position] != ":":
                    raise ValueError("invalid JSON object")
                position = walk(position + 1, [*path, str(key)])
                position = space(position)
                if content[position] == ",":
                    position = space(position + 1)
                else:
                    break
            return position + 1
        if content[position] == "[":
            position = space(position + 1)
            index = 0
            while content[position] != "]":
                position = walk(position, [*path, str(index)])
                index += 1
                position = space(position)
                if content[position] == ",":
                    position = space(position + 1)
                else:
                    break
            return position + 1
        _, end = decoder.raw_decode(content, position)
        title = ".".join(path) or "Value"
        pointer = "/".join(item.replace("~", "~0").replace("/", "~1") for item in path or ["value"])
        result.append(Section("json/" + pointer, title, position, end))
        return end

    walk(0, [])
    return result or [Section("body", "JSON", 0, len(content))]


def parse_sections(kind: str, content: str) -> list[Section]:
    if kind == "markdown":
        return _markdown(content)
    if kind == "transcript":
        return _transcript(content)
    if kind == "json":
        try:
            return _json(content)
        except (ValueError, IndexError, RecursionError):
            return [Section("body", "JSON", 0, len(content))]
    return [Section("body", "Body", 0, len(content))]


def section_for_span(kind: str, content: str, start: int, end: int) -> Section:
    for section in parse_sections(kind, content):
        if section.start_char <= start and end <= section.end_char:
            return section
    raise ValueError("Citation span crosses source sections")
