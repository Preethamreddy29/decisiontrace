"""Create and remove a disposable API-revoked source for restore verification."""

import os
import sys

from tools.eval_v03 import cleanup_eval_data, login, mutate


def fixture_id() -> str:
    value = os.environ.get("RESTORE_EVAL_ID", "")
    if len(value) != 12 or any(char not in "0123456789abcdef" for char in value):
        raise RuntimeError("RESTORE_EVAL_ID must be a 12-character hex token")
    return value


def main() -> None:
    token = fixture_id()
    origin = f"__restore_eval__/{token}"
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action == "cleanup":
        cleanup_eval_data(origin)
        return
    if action != "create":
        raise RuntimeError("expected create or cleanup")

    cleanup_eval_data(origin)
    author = login("cedar_auditor")
    body = {
        "kind": "markdown",
        "origin": origin,
        "content": f"# Restore probe\nA fictional Cedar approval note for restore case {token}.",
        "valid_from": "2026-07-01",
        "permissions": ["auditor", "owner"],
    }
    status, source = mutate("/v1/sources", author, body, key=f"source-{token}")
    assert status == 201, source
    status, revoked = mutate(
        f"/v1/sources/{source['source_id']}/revoke",
        author,
        {"reason": "Fixture withdrawn before backup"},
        source["etag"],
        key=f"revoke-{token}",
    )
    assert status == 200 and revoked["status"] == "revoked", revoked
    assert source["version_id"] in revoked["revoked_version_ids"], revoked
    print("Disposable source created and revoked through the API.")


if __name__ == "__main__":
    main()
