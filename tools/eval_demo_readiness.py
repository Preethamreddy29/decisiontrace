"""Exercise the exact file-upload to independent-review demo path."""

import atexit
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from tools.eval_v03 import call, cleanup_eval_data, later, login, mutate
from tools.eval_v05 import upload


FIXTURE = Path(__file__).resolve().parents[1] / "corpus" / "demo-invoice-holds.md"
ORIGIN_PATTERN = "upload:readiness-%"


def main() -> None:
    cleanup_eval_data(ORIGIN_PATTERN)
    atexit.register(lambda: cleanup_eval_data(ORIGIN_PATTERN))
    author = login("cedar_auditor")
    reviewer = login("cedar_reviewer")
    other_tenant = login("lumen_auditor")
    fixture = FIXTURE.read_bytes()
    filename = f"readiness-{uuid4().hex[:10]}.md"

    status, source = upload(author, filename, fixture)
    assert status == 201 and source["origin"] == f"upload:{filename}", source
    assert source["kind"] == "markdown" and source["version"] == 1
    assert len(source["sections"]) == 3

    status, draft = mutate("/v1/decision-contracts", author, {
        "title": "Invoice holds require finance approval before release from July 1",
        "valid_from": "2026-07-01", "evidence_version_ids": [source["version_id"]],
    })
    assert status == 201 and draft["status"] == "draft", draft
    status, rejected = mutate(f"/v1/decision-contracts/{draft['decision_id']}/review", author,
                              {"action": "approve"}, draft["etag"])
    assert status == 409, rejected
    status, approved = mutate(f"/v1/decision-contracts/{draft['decision_id']}/review", reviewer,
                              {"action": "approve"}, draft["etag"])
    assert status == 200 and approved["status"] == "approved", approved

    known_at = later(approved["recorded_at"])
    status, answer = mutate("/v1/query", author, {
        "question": "Who approves Cedar invoice holds on July 1?",
        "valid_on": "2026-07-01", "recorded_as_of": known_at, "answer_mode": "structured",
    }, key=f"eval-v03-readiness-{uuid4()}")
    assert status == 200 and answer["status"] == "answered", answer
    assert answer["claims"][0]["decision_version_id"] == approved["version_id"], answer
    citation = answer["claims"][0]["citations"][0]
    assert citation["version_id"] == source["version_id"]
    assert citation["section_id"] == "md/cedar-payment-controls/invoice-holds"

    path = (f"/v1/sources/{source['source_id']}/versions/{source['version_id']}"
            f"?recorded_as_of={quote(known_at)}")
    status, opened = call("GET", path, reviewer)
    assert status == 200, opened
    section = next(item for item in opened["sections"] if item["section_id"] == citation["section_id"])
    start, end = citation["start_char"], citation["end_char"]
    assert section["start_char"] <= start < end <= section["end_char"]
    assert opened["content"][start:end] == citation["quote"]
    status, _ = call("GET", path, other_tenant)
    assert status == 404

    cleanup_eval_data(ORIGIN_PATTERN)
    print("Demo readiness passed: fixture upload, distinct reviewer approval, cited answer, exact section, tenant denial, cleanup.")


if __name__ == "__main__":
    main()
