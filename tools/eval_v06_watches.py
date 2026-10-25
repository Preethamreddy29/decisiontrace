"""Live change-watch and independent classification checks."""

import atexit
from uuid import uuid4

from tools.eval_v03 import call, cleanup_eval_data, login, mutate


ORIGIN = "__v06_watch_eval__/%"


def main() -> None:
    cleanup_eval_data(ORIGIN)
    atexit.register(lambda: cleanup_eval_data(ORIGIN))
    author, reviewer, other = login("cedar_auditor"), login("cedar_reviewer"), login("lumen_auditor")
    unique = uuid4().hex[:10]
    policy_body = {
        "kind": "markdown", "origin": f"__v06_watch_eval__/policy-{unique}",
        "content": "# Invoice hold policy\n## Release\nInvoice holds require finance approval before release starting July 1.",
        "valid_from": "2026-07-01", "permissions": ["auditor", "owner"],
    }
    test_body = {
        "kind": "markdown", "origin": f"__v06_watch_eval__/test-{unique}",
        "content": "# Invoice hold test\n## Current assertion\nThe test requires finance approval before invoice release.",
        "valid_from": "2026-07-01", "permissions": ["auditor", "owner"],
    }
    status, policy = mutate("/v1/sources", author, policy_body)
    assert status == 201, policy
    status, downstream = mutate("/v1/sources", author, test_body)
    assert status == 201, downstream
    status, draft = mutate("/v1/decision-contracts", author, {
        "title": "Invoice holds require finance approval before release from July 1",
        "valid_from": "2026-07-01", "evidence_version_ids": [policy["version_id"]],
    })
    assert status == 201, draft
    status, approved = mutate(f"/v1/decision-contracts/{draft['decision_id']}/review", reviewer,
                              {"action": "approve"}, draft["etag"])
    assert status == 200 and approved["status"] == "approved", approved
    watch_body = {"decision_evidence_version_id": policy["version_id"],
                  "downstream_source_id": downstream["source_id"], "relation_type": "tests"}
    path = f"/v1/decision-contracts/{draft['decision_id']}/watches"
    assert mutate(path, other, watch_body)[0] == 404
    status, watch = mutate(path, author, watch_body)
    assert status == 201 and watch["baseline_source_version_id"] == downstream["version_id"], watch
    status, watches = call("GET", "/v1/change-watches", author)
    item = next(item for item in watches if item["watch_id"] == watch["watch_id"])
    assert status == 200 and item["status"] == "current", item
    assert item["decision_evidence"]["content"] == policy_body["content"]
    assert call("GET", "/v1/change-watches", other)[1] == []

    status, revised = mutate(f"/v1/sources/{downstream['source_id']}/versions", author,
                             {**test_body, "content": "# Invoice hold test\n## Current assertion\nThe test releases an invoice without finance approval."},
                             downstream["etag"])
    assert status == 201, revised
    item = next(item for item in call("GET", "/v1/change-watches", reviewer)[1] if item["watch_id"] == watch["watch_id"])
    assert item["status"] == "needs_review" and item["downstream"]["observed_version_id"] == revised["version_id"]
    assert item["downstream"]["baseline_content"] == test_body["content"]
    assert item["downstream"]["observed_content"] != item["downstream"]["baseline_content"]
    review_path = f"/v1/change-watches/{watch['watch_id']}/review"
    review_body = {"observed_source_version_id": revised["version_id"], "outcome": "drift",
                   "reason": "The test now omits the required finance approval."}
    assert mutate(review_path, author, review_body)[0] == 409
    assert mutate(review_path, other, review_body)[0] == 404
    assert mutate(review_path, reviewer, {**review_body, "observed_source_version_id": downstream["version_id"]})[0] == 409
    status, reviewed = mutate(review_path, reviewer, review_body)
    assert status == 200 and reviewed["status"] == "drift", reviewed
    item = next(item for item in call("GET", "/v1/change-watches", reviewer)[1] if item["watch_id"] == watch["watch_id"])
    assert item["status"] == "drift" and item["review"]["reviewed_by"] == "cedar_reviewer"
    assert mutate(review_path, reviewer, review_body)[0] == 409

    status, latest = mutate(f"/v1/sources/{downstream['source_id']}/versions", author,
                            {**test_body, "content": test_body["content"] + "\n## Correction\nApproval remains required."},
                            revised["etag"])
    assert status == 201, latest
    item = next(item for item in call("GET", "/v1/change-watches", reviewer)[1] if item["watch_id"] == watch["watch_id"])
    assert item["status"] == "needs_review" and item["downstream"]["observed_version_id"] == latest["version_id"]
    status, _ = mutate(f"/v1/sources/{downstream['source_id']}/revoke", author,
                       {"reason": "Disposable test source withdrawn"}, latest["etag"])
    assert status == 200
    assert all(item["watch_id"] != watch["watch_id"] for item in call("GET", "/v1/change-watches", reviewer)[1])
    cleanup_eval_data(ORIGIN)
    print("v0.6 change watches passed: approved link, version-change queue, exact evidence, independent review, tenant guard, revocation propagation.")


if __name__ == "__main__":
    main()
