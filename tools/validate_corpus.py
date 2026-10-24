"""Validate the authored synthetic corpus and its frozen file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
SOURCE_PATH = CORPUS / "sources.json"
GOLD_PATH = CORPUS / "gold.json"
MANIFEST_PATH = CORPUS / "manifest.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise ValueError(message)


def validate() -> dict:
    sources_doc = load(SOURCE_PATH)
    gold_doc = load(GOLD_PATH)
    sources = sources_doc["sources"]
    cases = gold_doc["cases"]
    if not sources_doc.get("fictional"):
        fail("corpus must be declared fictional")
    if gold_doc["corpus_version"] != sources_doc["corpus_version"]:
        fail("gold set references another corpus version")
    if len(cases) < 25:
        fail("at least 25 gold cases are required")
    if len({case["id"] for case in cases}) != len(cases):
        fail("duplicate gold case ID")
    if len({source["id"] for source in sources}) != len(sources):
        fail("duplicate source version ID")

    by_id = {source["id"]: source for source in sources}
    versions: dict[str, list[dict]] = {}
    for source in sources:
        versions.setdefault(source["source_id"], []).append(source)
        datetime.fromisoformat(source["recorded_at"].replace("Z", "+00:00"))
        date.fromisoformat(source["valid_from"])
        if source.get("superseded_at") and source["superseded_at"] <= source["recorded_at"]:
            fail(f"source superseded before recording: {source['id']}")
        if source.get("valid_to") and source["valid_to"] <= source["valid_from"]:
            fail(f"invalid half-open interval: {source['id']}")
        if source.get("corrects") and source["corrects"] not in by_id:
            fail(f"missing corrected version: {source['id']}")
    for source_id, history in versions.items():
        ordered = sorted(history, key=lambda item: item["version"])
        if [item["version"] for item in ordered] != list(range(1, len(ordered) + 1)):
            fail(f"non-consecutive versions: {source_id}")
        if [item["recorded_at"] for item in ordered] != sorted(item["recorded_at"] for item in ordered):
            fail(f"recorded time regresses: {source_id}")

    statuses = set()
    for case in cases:
        statuses.add(case["status"])
        as_of = datetime.fromisoformat(case["recorded_as_of"].replace("Z", "+00:00"))
        citations = case["citations"]
        if case["status"] in {"abstain", "denied"} and citations:
            fail(f"{case['id']} must not cite evidence")
        if case["status"] in {"answered", "conflict"} and not citations:
            fail(f"{case['id']} needs exact citations")
        for citation in citations:
            source = by_id.get(citation)
            if source is None:
                fail(f"{case['id']} cites missing {citation}")
            if source["tenant"] != case["tenant"]:
                fail(f"{case['id']} leaks another tenant's source")
            if case["role"] not in source["roles"]:
                fail(f"{case['id']} cites a source outside role permission")
            recorded = datetime.fromisoformat(source["recorded_at"].replace("Z", "+00:00"))
            if recorded > as_of:
                fail(f"{case['id']} cites evidence recorded in the future")
            if source.get("superseded_at"):
                superseded = datetime.fromisoformat(source["superseded_at"].replace("Z", "+00:00"))
                if superseded <= as_of and case.get("valid_on"):
                    fail(f"{case['id']} cites a superseded record as current evidence")
            if source.get("revoked_at"):
                revoked = datetime.fromisoformat(source["revoked_at"].replace("Z", "+00:00"))
                if revoked <= as_of:
                    fail(f"{case['id']} cites revoked evidence")
            valid_on = case.get("valid_on")
            if valid_on and not (source["valid_from"] <= valid_on < source.get("valid_to", "9999-12-31")):
                fail(f"{case['id']} cites evidence outside its valid interval")
    if not {"answered", "conflict", "abstain", "denied"}.issubset(statuses):
        fail("gold set needs answer, conflict, abstention, and permission denial")

    return {
        "corpus_version": sources_doc["corpus_version"],
        "gold_version": gold_doc["gold_version"],
        "license": "MIT",
        "source_versions": len(sources),
        "gold_cases": len(cases),
        "files": {
            "sources.json": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
            "gold.json": hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    result = validate()
    if args.write_manifest:
        MANIFEST_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    elif not MANIFEST_PATH.exists() or load(MANIFEST_PATH) != result:
        fail("manifest missing or out of date; review changes before regenerating it")
    print(f"Validated {result['source_versions']} source versions and {result['gold_cases']} gold cases.")


if __name__ == "__main__":
    main()
