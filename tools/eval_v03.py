"""Live end-to-end checks for the synthetic v0.3 source and review workflow."""

import json
import atexit
from datetime import datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from api.app.config import load_settings
from api.app.db import connect
from api.app.seed import stable_id


BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, token: str | None = None, body: dict | None = None, headers: dict | None = None):
    request = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {}), **(headers or {})},
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def login(account: str) -> str:
    status, result = call("POST", "/demo/login", body={"account": account, "passphrase": "local-demo-only"})
    assert status == 200, result
    return result["access_token"]


def mutate(path: str, token: str, body: dict, if_match: str | None = None, key: str | None = None):
    headers = {"Idempotency-Key": key or str(uuid4())}
    if if_match:
        headers["If-Match"] = if_match
    return call("POST", path, token, body, headers)


def ask(token: str, as_of: str, valid_on: str = "2026-06-25", key: str | None = None):
    status, result = mutate("/v1/query", token, {
        "question": "What does the approved manual override policy require for Cedar on June 25?",
        "valid_on": valid_on, "recorded_as_of": as_of, "answer_mode": "structured",
    }, key=key or f"eval-v03-{uuid4()}")
    assert status == 200, result
    return result


def later(value: str) -> str:
    return (datetime.fromisoformat(value) + timedelta(seconds=1)).isoformat()


def cleanup_eval_data(origin_pattern: str = "__v03_eval__/%"):
    """Keep the local demo empty of this script's disposable synthetic records."""
    with connect(load_settings().database_url) as connection:
        tenant = stable_id("tenant/cedar")
        rows = connection.execute(
            "SELECT id, source_id FROM source_versions WHERE tenant_id = %s AND origin LIKE %s",
            (tenant, origin_pattern),
        ).fetchall()
        if not rows:
            return
        version_ids = [row[0] for row in rows]
        source_ids = list({row[1] for row in rows})
        decisions = connection.execute(
            "SELECT id, decision_id FROM decision_versions WHERE tenant_id = %s "
            "AND evidence_version_ids && %s::uuid[]",
            (tenant, version_ids),
        ).fetchall()
        decision_version_ids = [row[0] for row in decisions]
        decision_ids = list({row[1] for row in decisions})
        watch_ids = [row[0] for row in connection.execute(
            "SELECT id FROM change_watches WHERE tenant_id = %s AND "
            "(decision_version_id = ANY(%s::uuid[]) OR downstream_source_id = ANY(%s::uuid[]))",
            (tenant, decision_version_ids, source_ids),
        ).fetchall()]
        subjects = version_ids + decision_version_ids + watch_ids
        connection.execute("DELETE FROM query_requests WHERE idempotency_key LIKE 'eval-v03-%'")
        connection.execute("DELETE FROM audit_events WHERE tenant_id = %s AND subject_id = ANY(%s::uuid[])", (tenant, subjects))
        connection.execute("DELETE FROM outbox_events WHERE tenant_id = %s AND payload->>'subject_id' = ANY(%s::text[])",
                           (tenant, [str(item) for item in subjects]))
        connection.execute("DELETE FROM mutation_requests WHERE response->>'source_id' = ANY(%s::text[]) "
                           "OR response->>'decision_id' = ANY(%s::text[]) OR response->>'watch_id' = ANY(%s::text[])",
                           ([str(item) for item in source_ids], [str(item) for item in decision_ids],
                            [str(item) for item in watch_ids]))
        connection.execute("DELETE FROM change_watches WHERE tenant_id = %s AND id = ANY(%s::uuid[])",
                           (tenant, watch_ids))
        connection.execute("DELETE FROM decision_versions WHERE tenant_id = %s AND decision_id = ANY(%s::uuid[])",
                           (tenant, decision_ids))
        connection.execute("DELETE FROM ingestion_jobs WHERE tenant_id = %s AND source_version_id = ANY(%s::uuid[])",
                           (tenant, version_ids))
        connection.execute("DELETE FROM source_versions WHERE tenant_id = %s AND id = ANY(%s::uuid[])",
                           (tenant, version_ids))


def main():
    cleanup_eval_data()
    atexit.register(cleanup_eval_data)
    author = login("cedar_auditor")
    reviewer = login("cedar_reviewer")
    viewer = login("cedar_viewer")
    lumen = login("lumen_auditor")
    unique = str(uuid4())[:8]
    body = {
        "kind": "markdown", "origin": f"__v03_eval__/{unique}",
        "content": f"Manual overrides require three reviewers from June 25 for Cedar case {unique}.",
        "valid_from": "2026-06-25", "permissions": ["auditor", "owner"],
    }
    status, _ = mutate("/v1/sources", author, {**body, "kind": "json"})
    assert status == 422
    status, _ = mutate("/v1/sources", author, {**body, "content": "x" * 10001})
    assert status == 422
    status, _ = mutate("/v1/sources", author, {**body, "permissions": ["viewer"]})
    assert status == 422

    status, source1 = mutate("/v1/sources", author, body, key=f"source-{unique}")
    assert status == 201 and source1["version"] == 1, source1
    status, duplicate = mutate("/v1/sources", author, body, key=f"source-{unique}")
    assert status == 201 and duplicate["version_id"] == source1["version_id"]
    status, _ = mutate("/v1/sources", author, {**body, "origin": "Different request"}, key=f"source-{unique}")
    assert status == 409
    status, _ = mutate("/v1/sources", viewer, body)
    assert status == 403
    status, _ = call("GET", f"/v1/sources/{source1['source_id']}/versions", lumen)
    assert status == 404

    corrected = {**body, "content": f"Manual overrides require four independent reviewers from June 25 for Cedar case {unique}."}
    path = f"/v1/sources/{source1['source_id']}/versions"
    status, source2 = mutate(path, author, corrected, source1["etag"])
    assert status == 201 and source2["version"] == 2 and source2["sha256"] != source1["sha256"], source2
    status, _ = mutate(path, author, corrected, source1["etag"])
    assert status == 409
    status, _ = mutate(path, reviewer, corrected, source2["etag"])
    assert status == 403
    status, source_versions = call("GET", path, reviewer)
    assert status == 200 and [item["version"] for item in source_versions] == [1, 2]
    assert source_versions[0]["content"] == body["content"] and source_versions[0]["superseded_at"]

    draft_body = {
        "title": f"Manual overrides require four reviewers from June 25: {unique}",
        "valid_from": "2026-06-25", "evidence_version_ids": [source2["version_id"]],
    }
    status, _ = mutate("/v1/decision-contracts", author, {**draft_body, "evidence_version_ids": [source1["version_id"]]})
    assert status == 409
    status, _ = mutate("/v1/decision-contracts", author, {**draft_body, "valid_from": "2026-06-24"})
    assert status == 409
    status, draft = mutate("/v1/decision-contracts", author, draft_body)
    assert status == 201 and draft["status"] == "draft" and draft["version"] == 1, draft
    assert ask(author, draft["recorded_at"])["status"] == "answered"  # Existing seeded policy, not the draft.
    pre_review = ask(author, draft["recorded_at"])
    assert all(claim.get("decision_version_id") is None for claim in pre_review["claims"])
    review_path = f"/v1/decision-contracts/{draft['decision_id']}/review"
    status, _ = mutate(review_path, author, {"action": "approve"}, draft["etag"])
    assert status == 409
    status, _ = mutate(review_path, viewer, {"action": "approve"}, draft["etag"])
    assert status == 403
    review_key = f"review-{unique}"
    status, approved = mutate(review_path, reviewer, {"action": "approve"}, draft["etag"], review_key)
    assert status == 200 and approved["status"] == "approved" and approved["version"] == 2, approved
    status, same_review = mutate(review_path, reviewer, {"action": "approve"}, draft["etag"], review_key)
    assert status == 200 and same_review["version_id"] == approved["version_id"]
    status, _ = mutate(review_path, reviewer, {"action": "approve"}, draft["etag"])
    assert status == 409
    status, history = call("GET", f"/v1/decision-contracts/{draft['decision_id']}/history", reviewer)
    assert status == 200 and [item["status"] for item in history] == ["draft", "approved"]
    status, _ = call("GET", f"/v1/decision-contracts/{draft['decision_id']}/history", lumen)
    assert status == 404
    status, _ = call("GET", "/v1/decision-contracts", viewer)
    assert status == 403

    after_review = approved["recorded_at"]
    answer = ask(author, after_review)
    assert answer["status"] == "answered" and answer["claims"][0]["decision_version_id"] == approved["version_id"], answer
    citation = answer["claims"][0]["citations"][0]
    assert citation["version_id"] == source2["version_id"]
    status, opened = call("GET", f"/v1/sources/{source2['source_id']}/versions/{source2['version_id']}?recorded_as_of={quote(after_review)}", reviewer)
    assert status == 200 and opened["content"][citation["start_char"]:citation["end_char"]] == citation["quote"]
    assert ask(author, draft["recorded_at"])["claims"][0].get("decision_version_id") is None

    status, source3 = mutate(path, author, {**corrected, "content": f"Manual overrides require five reviewers from June 25 for Cedar case {unique}."}, source2["etag"])
    assert status == 201 and source3["version"] == 3
    current = ask(author, later(source3["recorded_at"]))
    assert current["status"] == "abstain" and "no longer available" in current["abstention_reason"], current
    historical = ask(author, after_review)
    assert historical["status"] == "answered" and historical["claims"][0]["citations"][0]["version_id"] == source2["version_id"]
    status, rejected_draft = mutate("/v1/decision-contracts", author, {
        **draft_body, "title": f"Manual overrides require five reviewers from June 25: {unique}",
        "evidence_version_ids": [source3["version_id"]],
    })
    assert status == 201
    status, rejected = mutate(f"/v1/decision-contracts/{rejected_draft['decision_id']}/review", reviewer,
                              {"action": "reject", "reason": "Not accepted in the fictional demo"}, rejected_draft["etag"])
    assert status == 200 and rejected["status"] == "rejected"
    assert ask(author, later(rejected["recorded_at"]))["status"] == "abstain"
    with connect(load_settings().database_url) as connection:
        subjects = [source1["version_id"], source2["version_id"], source3["version_id"],
                    draft["version_id"], approved["version_id"], rejected_draft["version_id"], rejected["version_id"]]
        audit_count = connection.execute(
            "SELECT count(*) FROM audit_events WHERE tenant_id = %s AND subject_id = ANY(%s::uuid[])",
            (stable_id("tenant/cedar"), subjects),
        ).fetchone()[0]
        outbox_count = connection.execute(
            "SELECT count(*) FROM outbox_events WHERE tenant_id = %s AND payload->>'subject_id' = ANY(%s::text[])",
            (stable_id("tenant/cedar"), subjects),
        ).fetchone()[0]
    assert audit_count == outbox_count == len(subjects), (audit_count, outbox_count)
    cleanup_eval_data()
    print("v0.3 live workflow passed: versioning, idempotency, review separation, historical answers, stale evidence, and tenant/role checks.")


if __name__ == "__main__":
    main()
