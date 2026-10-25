"""Structure-aware citation and second-topic live demo checks."""

import atexit
from urllib.parse import quote
from uuid import uuid4

from api.app.sections import parse_sections
from tools.eval_v03 import call, cleanup_eval_data, later, login, mutate


def parser_checks() -> None:
    original = "# Cedar controls\n## Invoice holds\nInvoice holds require finance approval.\n## Scope\nFictional invoices only."
    edited = original.replace("Fictional invoices only.", "Fictional Cedar invoices only.")
    before = parse_sections("markdown", original)
    after = parse_sections("markdown", edited)
    assert [item.section_id for item in before] == [item.section_id for item in after]
    assert [item.section_id for item in before] == ["md/cedar-controls", "md/cedar-controls/invoice-holds", "md/cedar-controls/scope"]
    assert original[before[1].start_char:before[1].end_char].startswith("## Invoice holds")
    repeated = "# Policy\n## Rule\nOne.\n# Policy\n## Rule\nTwo."
    assert [item.section_id for item in parse_sections("markdown", repeated)] == [
        "md/policy", "md/policy/rule", "md/policy~2", "md/policy~2/rule",
    ]
    transcript = "[10:00] Ada: Start the review.\n[10:01] Ben: Approve the release."
    assert [item.section_id for item in parse_sections("transcript", transcript)] == ["turn/ada/10:00", "turn/ben/10:01"]
    assert [item.section_id for item in parse_sections("transcript", "[10:00] Ada: One.\n[10:00] Ada: Two.")] == ["turn/ada/10:00", "turn/ada/10:00~2"]
    document = '{"policy": {"owner": "finance", "enabled": true}}'
    sections = parse_sections("json", document)
    assert [item.section_id for item in sections] == ["json/policy/owner", "json/policy/enabled"]
    assert document[sections[0].start_char:sections[0].end_char] == '"finance"'


def ask(token: str, as_of: str, valid_on: str) -> dict:
    status, result = mutate("/v1/query", token, {
        "question": "Who approves Cedar invoice holds before release?",
        "valid_on": valid_on, "recorded_as_of": as_of, "answer_mode": "structured",
    }, key=f"eval-v03-v04-{uuid4()}")
    assert status == 200, result
    return result


def main() -> None:
    parser_checks()
    cleanup_eval_data("__v04_eval__/%")
    atexit.register(lambda: cleanup_eval_data("__v04_eval__/%"))
    author, reviewer, lumen = login("cedar_auditor"), login("cedar_reviewer"), login("lumen_auditor")
    unique = str(uuid4())[:8]
    body = {
        "kind": "markdown", "origin": f"__v04_eval__/{unique}",
        "content": f"# Cedar payment controls\n## Invoice holds\nInvoice holds require finance approval before release for Cedar case {unique}.\n## Scope\nThis fictional policy applies to Cedar invoices.",
        "valid_from": "2026-07-01", "permissions": ["auditor", "owner"],
    }
    status, source = mutate("/v1/sources", author, body)
    assert status == 201, source
    status, draft = mutate("/v1/decision-contracts", author, {
        "title": f"Invoice holds require finance approval before release {unique}",
        "valid_from": "2026-07-01", "evidence_version_ids": [source["version_id"]],
    })
    assert status == 201, draft
    status, approved = mutate(f"/v1/decision-contracts/{draft['decision_id']}/review", reviewer,
                              {"action": "approve"}, draft["etag"])
    assert status == 200, approved
    answer = ask(author, later(approved["recorded_at"]), "2026-07-01")
    assert answer["status"] == "answered" and answer["claims"][0]["decision_version_id"] == approved["version_id"], answer
    citation = answer["claims"][0]["citations"][0]
    assert citation["section_id"] == "md/cedar-payment-controls/invoice-holds", citation
    status, opened = call("GET", f"/v1/sources/{source['source_id']}/versions/{source['version_id']}?recorded_as_of={quote(answer['recorded_as_of'])}", reviewer)
    assert status == 200, opened
    section = next(item for item in opened["sections"] if item["section_id"] == citation["section_id"])
    assert section["start_char"] <= citation["start_char"] < citation["end_char"] <= section["end_char"]
    assert opened["content"][citation["start_char"]:citation["end_char"]] == citation["quote"]
    status, _ = call("GET", f"/v1/sources/{source['source_id']}/versions/{source['version_id']}?recorded_as_of={quote(answer['recorded_as_of'])}", lumen)
    assert status == 404
    correction = {**body, "content": body["content"].replace("fictional policy", "fictional Cedar policy")}
    status, revised = mutate(f"/v1/sources/{source['source_id']}/versions", author, correction, source["etag"])
    assert status == 201, revised
    assert ask(author, later(revised["recorded_at"]), "2026-07-01")["status"] == "abstain"
    assert ask(author, approved["recorded_at"], "2026-07-01")["status"] == "answered"
    cleanup_eval_data("__v04_eval__/%")
    print("v0.4 passed: structured Markdown/transcript/JSON sections, second-topic approval, exact citation, tenant scope, and correction history.")


if __name__ == "__main__":
    main()
