"""Diagnostic evaluation of the v0.5 draft; a gate only for reviewed labels."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from api.app.config import load_settings
from api.app.db import connect
from tools.eval_v03 import call, login, mutate


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "corpus" / "holdout_v05_draft.json"


def evaluate(path: Path) -> bool:
    with connect(load_settings().database_url) as connection:
        connection.execute("DELETE FROM query_requests WHERE idempotency_key LIKE 'holdout-v05-%'")
    suite = json.loads(path.read_text(encoding="utf-8"))
    reviewed = suite.get("status") == "independently-reviewed" and bool(suite.get("reviewer"))
    cases = suite["cases"]
    assert len(cases) >= 20 and len({case["id"] for case in cases}) == len(cases)
    tokens = {case["account"]: login(case["account"]) for case in cases}
    correct, supported, exact = 0, 0, 0
    misses: list[str] = []

    for case in cases:
        token = tokens[case["account"]]
        status, result = mutate("/v1/query", token, {
            "question": case["question"], "valid_on": case["valid_on"],
            "recorded_as_of": case["recorded_as_of"], "answer_mode": "structured",
        }, key=f"holdout-v05-{uuid4()}")
        if status != 200:
            misses.append(f"{case['id']}: HTTP {status}")
            continue
        claims = result["claims"]
        citations = [citation for claim in claims for citation in claim["citations"]]
        labels = {citation["label"] for citation in citations}
        answer_text = " ".join(claim["text"] for claim in claims).lower()
        status_ok = result["status"] == case["status"]
        label_ok = set(case["required_labels"]) <= labels
        term_ok = all(term.lower() in answer_text for term in case["required_terms"])
        no_citation_ok = case["status"] not in {"denied", "abstain"} or not citations
        if status_ok:
            correct += 1
        if status_ok and label_ok and term_ok and no_citation_ok:
            supported += 1
        else:
            misses.append(
                f"{case['id']}: expected {case['status']} {case['required_labels']} {case['required_terms']}; "
                f"got {result['status']} {sorted(labels)} {answer_text[:140]}"
            )

        citation_ok = True
        for citation in citations:
            path = (f"/v1/sources/{citation['source_id']}/versions/{citation['version_id']}"
                    f"?recorded_as_of={quote(case['recorded_as_of'])}")
            source_status, source = call("GET", path, token)
            if source_status != 200:
                citation_ok = False
                break
            start, end = citation["start_char"], citation["end_char"]
            section = next((part for part in source["sections"] if part["section_id"] == citation["section_id"]), None)
            if (source["content"][start:end] != citation["quote"] or section is None
                    or not section["start_char"] <= start < end <= section["end_char"]):
                citation_ok = False
                break
        if citation_ok:
            exact += 1
        else:
            misses.append(f"{case['id']}: citation failed authorized source/span/section verification")

    count = len(cases)
    print(f"v0.5 holdout: {count} cases; status {correct}/{count}; labels+terms {supported}/{count}; exact citations {exact}/{count}")
    print("Label status:", "independently reviewed" if reviewed else "DRAFT — diagnostic, not product-gate evidence")
    for miss in misses:
        print("MISS", miss)
    with connect(load_settings().database_url) as connection:
        connection.execute("DELETE FROM query_requests WHERE idempotency_key LIKE 'holdout-v05-%'")
    if reviewed and misses:
        raise SystemExit(1)
    return not misses


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DRAFT)
    args = parser.parse_args()
    evaluate(args.suite)
