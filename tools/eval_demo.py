"""Check the historical-policy demo against independently authored seed labels."""

import json
from pathlib import Path

from api.app.config import load_settings
from api.app.demo import DemoQuery, answer


ROOT = Path(__file__).resolve().parents[1]
cases = {item["id"]: item for item in json.loads((ROOT / "corpus/gold.json").read_text())["cases"]}
database_url = load_settings().database_url
critical_phrases = {
    "Q01": ("two independent reviewers", "10000"),
    "Q02": ("one reviewer", "10000"),
    "Q03": ("disabled", "standard review queue"),
    "Q08": ("two independent reviewers",),
    "Q09": ("disabled",),
    "Q18": ("unapproved draft", "approved DEC-CEDAR-002"),
    "Q25": ("untrusted data", "authorization"),
}

for case_id in cases:
    case = cases[case_id]
    query = DemoQuery(
        question=case["question"], tenant=case["tenant"], role=case["role"],
        valid_on=case.get("valid_on", "2026-06-30"), recorded_as_of=case["recorded_as_of"],
    )
    result = answer(database_url, query)
    actual = {citation["label"] for citation in result["citations"]}
    required = set(case["citations"])
    assert result["status"] == case["status"], (case_id, result)
    assert required <= actual, (case_id, actual, required)
    assert all(phrase.lower() in result["answer"].lower() for phrase in critical_phrases.get(case_id, ())), (case_id, result["answer"])
    if result["status"] in ("abstain", "denied"):
        assert not actual, (case_id, actual)
    assert all(citation["text"] for citation in result["citations"]), case_id
    print(f"{case_id}: {result['status']} — {', '.join(sorted(actual))}")

early = answer(database_url, DemoQuery(
    question="What manual-override policy was valid for Cedar on 10 May?",
    valid_on="2026-05-10", recorded_as_of="2026-05-10T23:59:59Z",
))
assert all(item["recorded_at"] <= "2026-05-10T23:59:59+00:00" for item in early["citations"])
assert "SRC-MEETING-001-v2" not in {item["label"] for item in early["citations"]}
print("Historical visibility check passed.")

unknown = answer(database_url, DemoQuery(
    question="How many policy documents are in the archive?",
    valid_on="2026-06-30", recorded_as_of="2026-06-30T00:00:00Z",
))
assert unknown["status"] == "abstain" and not unknown["citations"]
print("Unsupported-question abstention passed.")
