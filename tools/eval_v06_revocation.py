"""Live source-revocation checks using disposable fictional evidence."""

import atexit
from urllib.parse import quote
from uuid import uuid4

from api.app.config import load_settings
from api.app.db import connect
from api.app.migrate import migrate
from api.app.seed import stable_id
from tools.eval_v03 import call, cleanup_eval_data, later, login, mutate


ORIGIN = "__v06_revoke_eval__/%"


def main() -> None:
    cleanup_eval_data(ORIGIN)
    atexit.register(lambda: cleanup_eval_data(ORIGIN))
    author, reviewer, other = login("cedar_auditor"), login("cedar_reviewer"), login("lumen_auditor")
    unique = uuid4().hex[:10]
    body = {
        "kind": "markdown", "origin": f"__v06_revoke_eval__/{unique}",
        "content": f"# Cedar invoice controls\n## Invoice holds\nInvoice holds require finance approval before release starting July 1. Case {unique}.",
        "valid_from": "2026-07-01", "permissions": ["auditor", "owner"],
    }
    source_key = f"source-{unique}"
    status, source = mutate("/v1/sources", author, body, key=source_key)
    assert status == 201, source
    decision_body = {
        "title": "Invoice holds require finance approval before release from July 1",
        "valid_from": "2026-07-01", "evidence_version_ids": [source["version_id"]],
    }
    decision_key = f"decision-{unique}"
    status, draft = mutate("/v1/decision-contracts", author, decision_body, key=decision_key)
    assert status == 201, draft
    status, approved = mutate(f"/v1/decision-contracts/{draft['decision_id']}/review", reviewer,
                              {"action": "approve"}, draft["etag"])
    assert status == 200 and approved["status"] == "approved", approved
    known = later(approved["recorded_at"])
    query_key = f"eval-v03-v06-{unique}"
    status, answer = mutate("/v1/query", author, {
        "question": "Who approves Cedar invoice holds on July 1?",
        "valid_on": "2026-07-01", "recorded_as_of": known, "answer_mode": "structured",
        "source_ids": [source["source_id"]],
    }, key=query_key)
    assert status == 200 and answer["status"] == "answered", answer
    path = f"/v1/sources/{source['source_id']}/versions/{source['version_id']}?recorded_as_of={quote(known)}"
    assert call("GET", path, author)[0] == 200

    corrected_body = {**body, "content": body["content"] + "\n## Note\nThe finance approval step remains required."}
    version_key = f"version-{unique}"
    status, corrected = mutate(f"/v1/sources/{source['source_id']}/versions", author,
                               corrected_body, source["etag"], key=version_key)
    assert status == 201 and corrected["version"] == 2, corrected
    endpoint = f"/v1/sources/{source['source_id']}/revoke"
    status, _ = mutate(endpoint, other, {"reason": "Source withdrawn from fictional demo"}, corrected["etag"])
    assert status == 404
    status, _ = mutate(endpoint, reviewer, {"reason": "Source withdrawn from fictional demo"}, corrected["etag"])
    assert status == 403
    status, _ = mutate(endpoint, author, {"reason": "Source withdrawn from fictional demo"}, source["etag"])
    assert status == 409
    key = f"revoke-{unique}"
    reason = {"reason": "Source withdrawn from fictional demo"}
    status, revoked = mutate(endpoint, author, reason, corrected["etag"], key=key)
    assert status == 200 and revoked["status"] == "revoked", revoked
    assert set(revoked["revoked_version_ids"]) == {source["version_id"], corrected["version_id"]}
    assert mutate(endpoint, author, reason, corrected["etag"], key=key) == (200, revoked)
    assert mutate(endpoint, author, reason, corrected["etag"])[0] == 409
    assert call("GET", path, author)[0] == 404
    assert mutate("/v1/sources", author, body, key=source_key)[1] == {"source_id": source["source_id"], "status": "revoked"}
    assert mutate(f"/v1/sources/{source['source_id']}/versions", author, corrected_body,
                  source["etag"], key=version_key)[1] == {"source_id": source["source_id"], "status": "revoked"}
    assert mutate("/v1/decision-contracts", author, decision_body, key=decision_key)[1] == {
        "decision_id": draft["decision_id"], "status": "evidence_revoked"}
    assert call("GET", f"/v1/sources/{source['source_id']}/versions", author)[0] == 404
    assert call("GET", f"/v1/decision-contracts/{draft['decision_id']}/history", reviewer)[0] == 404
    assert mutate(f"/v1/sources/{source['source_id']}/versions", author, body, corrected["etag"])[0] == 409
    status, listing = call("GET", "/v1/sources", author)
    assert status == 200 and all(item["source_id"] != source["source_id"] for item in listing)

    migrate()  # A restart/backfill must not recreate chunks for revoked evidence.

    with connect(load_settings().database_url) as connection:
        tenant = stable_id("tenant/cedar")
        assert connection.execute("SELECT count(*) FROM source_versions WHERE tenant_id = %s AND source_id = %s AND revoked_at IS NOT NULL",
                                  (tenant, source["source_id"])).fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM source_chunks WHERE tenant_id = %s AND source_version_id = ANY(%s::uuid[])",
                                  (tenant, revoked["revoked_version_ids"])).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM query_requests WHERE idempotency_key = %s", (query_key,)).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM audit_events WHERE tenant_id = %s AND action = 'source.revoked' AND subject_id = %s",
                                  (tenant, corrected["version_id"])).fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM outbox_events WHERE tenant_id = %s AND event_type = 'source.revoked' AND payload->>'subject_id' = %s",
                                  (tenant, corrected["version_id"])).fetchone()[0] == 1
    cleanup_eval_data(ORIGIN)
    print("v0.6 revocation passed: both versions hidden, cache/chunks removed, tenant/author/stale/retry guards, audit/outbox.")


if __name__ == "__main__":
    main()
