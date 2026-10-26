"""Check that in-flight evidence reads and revocation have a tenant-level order."""

import atexit
import threading
import time
from uuid import uuid4

from api.app.auth import ACCOUNTS
from api.app.config import load_settings
from api.app.db import connect
from api.app.locks import evidence_lock_key
from tools.eval_v03 import call, cleanup_eval_data, login, mutate


ORIGIN = "__v07_race_eval__/%"


def _in_thread(work):
    result = {}
    started = threading.Event()

    def run():
        started.set()
        try:
            result["value"] = work()
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert started.wait(2)
    return thread, result


def main() -> None:
    cleanup_eval_data(ORIGIN)
    atexit.register(lambda: cleanup_eval_data(ORIGIN))
    token = login("cedar_auditor")
    actor = ACCOUNTS["cedar_auditor"]
    lock_key = evidence_lock_key(actor)
    database_url = load_settings().database_url

    with connect(database_url) as blocker:
        blocker.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
        query_thread, query_result = _in_thread(lambda: mutate("/v1/query", token, {
            "question": "Can Cedar still use a manual override on May 21?",
            "valid_on": "2026-05-21", "recorded_as_of": "2026-06-30T00:00:00Z",
            "answer_mode": "structured",
        }, key=f"eval-v03-v07-{uuid4()}"))
        time.sleep(0.3)
        assert "value" not in query_result and "error" not in query_result, "query bypassed tenant read lock"
        blocker.commit()
    query_thread.join(10)
    assert not query_thread.is_alive() and "error" not in query_result, query_result
    assert query_result["value"][0] == 200, query_result

    source_body = {
        "kind": "markdown", "origin": f"__v07_race_eval__/{uuid4().hex[:10]}",
        "content": "# Fictional policy\n## Invoice holds\nFinance approval is required before invoice release.",
        "valid_from": "2026-07-01", "permissions": ["auditor", "owner"],
    }
    status, source = mutate("/v1/sources", token, source_body)
    assert status == 201, source
    with connect(database_url) as blocker:
        blocker.execute("SELECT pg_advisory_xact_lock_shared(%s)", (lock_key,))
        revoke_thread, revoke_result = _in_thread(lambda: mutate(
            f"/v1/sources/{source['source_id']}/revoke", token,
            {"reason": "Disposable concurrency fixture withdrawn"}, source["etag"]))
        time.sleep(0.3)
        assert "value" not in revoke_result and "error" not in revoke_result, "revocation bypassed tenant write lock"
        blocker.commit()
    revoke_thread.join(10)
    assert not revoke_thread.is_alive() and "error" not in revoke_result, revoke_result
    assert revoke_result["value"][0] == 200, revoke_result
    assert call("GET", f"/v1/sources/{source['source_id']}/versions", token)[0] == 404
    cleanup_eval_data(ORIGIN)
    print("Tenant evidence ordering passed: query waits for writer, revocation waits for reader, revoked source stays hidden.")


if __name__ == "__main__":
    main()
