"""Live HTTP proof for the v0.2 synthetic query, citation, and demo identity flow."""

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "corpus/paraphrases_v02.json").read_text(encoding="utf-8"))["cases"]
BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, body: dict | None = None, token: str | None = None, key: str | None = None):
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if key:
        headers["Idempotency-Key"] = key
    request = Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


tokens = {}
for account in ("cedar_auditor", "cedar_viewer", "lumen_auditor"):
    status, login = call("POST", "/demo/login", {"account": account, "passphrase": "local-demo-only"})
    assert status == 200, (account, status, login)
    tokens[account] = login["access_token"]
    status, session = call("GET", "/demo/session", token=tokens[account])
    assert status == 200 and session["account"] == account, (account, status, session)

first_answer = None
lumen_source_id = None
later_citation = None
for case in CASES:
    body = {
        "question": case["question"], "valid_on": case["valid_on"],
        "recorded_as_of": case["recorded_as_of"], "answer_mode": "structured",
    }
    status, answer = call("POST", "/v1/query", body, tokens[case["account"]], str(uuid4()))
    assert status == 200, (case["id"], status, answer)
    assert answer["status"] == case["status"], (case["id"], answer)
    claims = answer["claims"]
    labels = {citation["label"] for claim in claims for citation in claim["citations"]}
    assert set(case["required_labels"]) <= labels, (case["id"], labels)
    combined = " ".join(claim["text"] for claim in claims).lower()
    assert all(term.lower() in combined for term in case["required_terms"]), (case["id"], combined)
    if case["status"] in ("abstain", "denied"):
        assert not claims and not labels, case["id"]
    for claim in claims:
        assert claim["citations"], case["id"]
        for citation in claim["citations"]:
            path = (f"/v1/sources/{citation['source_id']}/versions/{citation['version_id']}?"
                    + urlencode({"recorded_as_of": answer["recorded_as_of"]}))
            source_status, source = call("GET", path, token=tokens[case["account"]])
            assert source_status == 200, (case["id"], source_status, source)
            assert source["content"][citation["start_char"]:citation["end_char"]] == citation["quote"]
            assert claim["text"] == citation["quote"]
            if case["id"] == "P01":
                first_answer = (case, body, answer, citation)
            if case["id"] == "P02":
                later_citation = citation
            if case["id"] == "P11":
                lumen_source_id = citation["source_id"]
    print(f"{case['id']}: {answer['status']} — {', '.join(sorted(labels))}")

assert first_answer is not None
assert lumen_source_id is not None and later_citation is not None
case, body, original, citation = first_answer
key = str(uuid4())
status, saved = call("POST", "/v1/query", body, tokens[case["account"]], key)
assert status == 200
status, replay = call("POST", "/v1/query", body, tokens[case["account"]], key)
assert status == 200 and replay["answer_id"] == saved["answer_id"]
status, problem = call("POST", "/v1/query", {**body, "question": "Different question"}, tokens[case["account"]], key)
assert status == 409, (status, problem)

status, problem = call("POST", "/v1/query", body, key=str(uuid4()))
assert status == 401, (status, problem)
status, problem = call("POST", "/v1/query", body, tokens[case["account"]] + "x", str(uuid4()))
assert status == 401, (status, problem)
status, problem = call("POST", "/v1/query", body, "%%%", str(uuid4()))
assert status == 401, (status, problem)
status, problem = call("POST", "/v1/query", {**body, "tenant": "lumen"}, tokens[case["account"]], str(uuid4()))
assert status == 422, (status, problem)
status, problem = call("POST", "/demo/login", {"account": "cedar_auditor", "passphrase": "wrong"})
assert status == 401, (status, problem)
status, filtered = call("POST", "/v1/query", {**body, "source_ids": [lumen_source_id]}, tokens["cedar_auditor"], str(uuid4()))
assert status == 200 and filtered["status"] == "abstain" and not filtered["claims"], (status, filtered)
status, unrelated = call("POST", "/v1/query", {**body, "question": "What is Cedar's data retention policy?"}, tokens["cedar_auditor"], str(uuid4()))
assert status == 200 and unrelated["status"] == "abstain" and not unrelated["claims"], (status, unrelated)

path = (f"/v1/sources/{citation['source_id']}/versions/{citation['version_id']}?"
        + urlencode({"recorded_as_of": original["recorded_as_of"]}))
status, problem = call("GET", path, token=tokens["lumen_auditor"])
assert status == 404, (status, problem)
status, problem = call("GET", path)
assert status == 401, (status, problem)
early_path = (f"/v1/sources/{later_citation['source_id']}/versions/{later_citation['version_id']}?"
              + urlencode({"recorded_as_of": "2026-05-10T23:59:59Z"}))
status, problem = call("GET", early_path, token=tokens["cedar_auditor"])
assert status == 404, (status, problem)

print(f"v0.2 live evaluation passed: {len(CASES)} new questions, exact citation spans, idempotency, and access checks.")
