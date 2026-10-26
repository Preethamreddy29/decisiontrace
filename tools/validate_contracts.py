"""Dependency-free structural checks for draft JSON contracts.

This is not a substitute for a complete OpenAPI/JSON Schema validator.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.app.events import EVENT_TYPES, EVENT_VERSION, valid_event


CONTRACTS = ROOT / "contracts"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def resolve(document: dict, reference: str):
    if not reference.startswith("#/"):
        raise ValueError(f"unsupported external reference: {reference}")
    target = document
    for part in reference[2:].split("/"):
        target = target[part.replace("~1", "/").replace("~0", "~")]
    return target


def check() -> None:
    api = load(CONTRACTS / "openapi.json")
    events = load(CONTRACTS / "events.schema.json")
    if api.get("openapi") != "3.1.0" or not api.get("security"):
        raise ValueError("expected secured OpenAPI 3.1.0 contract")
    operations = []
    for path, methods in api["paths"].items():
        path_fields = set(re.findall(r"\{([^}]+)\}", path))
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            operations.append(operation["operationId"])
            params = {p["name"] for p in operation.get("parameters", []) if p["in"] == "path" and p.get("required")}
            if params != path_fields:
                raise ValueError(f"path parameters mismatch: {method.upper()} {path}")
            if not operation.get("responses"):
                raise ValueError(f"missing responses: {method.upper()} {path}")
            if method in {"post", "put", "patch"} and "requestBody" not in operation:
                raise ValueError(f"missing body: {method.upper()} {path}")
    if len(operations) != len(set(operations)):
        raise ValueError("duplicate operationId")
    for document in (api, events):
        for node in walk(document):
            if "$ref" in node:
                resolve(document, node["$ref"])
    if set(api["components"]["schemas"]["Answer"]["properties"]["status"]["enum"]) != {"answered", "conflict", "abstain", "denied"}:
        raise ValueError("answer status contract diverges from the gold set")
    if set(events["properties"]["event_type"]["enum"]) != EVENT_TYPES:
        raise ValueError("outbox schema and worker event registry disagree")
    if events["properties"]["event_version"]["const"] != EVENT_VERSION:
        raise ValueError("outbox schema and worker event version disagree")
    if not valid_event("source.revoked", 1, {"subject_id": "00000000-0000-0000-0000-000000000001"}):
        raise ValueError("current source event must validate")
    if valid_event("source.revoked", 2, {"subject_id": "00000000-0000-0000-0000-000000000001"}):
        raise ValueError("future event version must be rejected")
    print(f"Structural contract checks passed: {len(operations)} API operations and {len(EVENT_TYPES)} local event types.")


if __name__ == "__main__":
    check()
