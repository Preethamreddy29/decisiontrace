"""Live intake/index checks plus strict external-token verification cases."""
import atexit
import base64
import hashlib
import json
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from api.app.config import load_settings
from api.app.db import connect
from api.app.indexing import MAX_CHARS, chunk_source
from api.app.oidc import OidcConfig, verify_oidc_token
from api.app.seed import stable_id
from tools.eval_v03 import BASE, call, login, mutate


def b64int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def oidc_checks() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = key.public_key().public_numbers()
    jwks = {"keys": [{"kty": "RSA", "kid": "fixture-1", "use": "sig", "alg": "RS256",
                      "n": b64int(numbers.n), "e": b64int(numbers.e)}]}
    config = OidcConfig("https://identity.example.test", "decisiontrace-api",
                        "https://identity.example.test/jwks", frozenset({"cedar", "lumen"}))
    now = int(time.time())
    claims = {"iss": config.issuer, "aud": config.audience, "sub": "external-reviewer",
              "tenant": "cedar", "role": "auditor", "iat": now, "exp": now + 300}

    def signed(payload: dict, signing_key=key, algorithm="RS256") -> str:
        return jwt.encode(payload, signing_key, algorithm=algorithm, headers={"kid": "fixture-1"})

    actor = verify_oidc_token(signed(claims), config, jwks)
    assert actor.tenant == "cedar" and actor.role == "auditor" and actor.account.endswith("|external-reviewer")
    for change in ({"iss": "https://other.example.test"}, {"aud": "wrong-api"},
                   {"tenant": "unknown"}, {"role": "owner-admin"}, {"exp": now - 100},
                   {"sub": ""}):
        try:
            verify_oidc_token(signed({**claims, **change}), config, jwks)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError(f"OIDC token accepted forbidden claim: {change}")
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    try:
        verify_oidc_token(signed(claims, wrong_key), config, jwks)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("OIDC token accepted a bad signature")
    try:
        verify_oidc_token(signed(claims, "demo-secret-with-at-least-32-bytes-long", "HS256"), config, jwks)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("OIDC token accepted a different algorithm")


def upload(token: str, filename: str, body: bytes, kind: str = "markdown") -> tuple[int, dict]:
    path = "/v1/sources/upload?" + urlencode({"kind": kind, "valid_from": "2026-07-01", "permissions": "auditor,owner"})
    request = Request(BASE + path, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid4()),
        "X-Source-Filename": filename, "Content-Type": "application/octet-stream",
    })
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def cleanup() -> None:
    with connect(load_settings().database_url) as connection:
        rows = connection.execute(
            "SELECT id, source_id FROM source_versions WHERE origin LIKE 'upload:v05-%' "
            "OR origin LIKE 'connector:fictional-push/v05-%'"
        ).fetchall()
        if not rows:
            return
        versions = [row[0] for row in rows]
        sources = list({row[1] for row in rows})
        connection.execute("DELETE FROM connector_objects WHERE source_id = ANY(%s::uuid[])", (sources,))
        connection.execute("DELETE FROM query_requests WHERE idempotency_key LIKE 'eval-v05-%'")
        connection.execute("DELETE FROM audit_events WHERE subject_id = ANY(%s::uuid[])", (versions,))
        connection.execute("DELETE FROM outbox_events WHERE payload->>'subject_id' = ANY(%s::text[])",
                           ([str(item) for item in versions],))
        connection.execute("DELETE FROM mutation_requests WHERE response->>'source_id' = ANY(%s::text[])",
                           ([str(item) for item in sources],))
        connection.execute("DELETE FROM ingestion_jobs WHERE source_version_id = ANY(%s::uuid[])", (versions,))
        connection.execute("DELETE FROM source_versions WHERE id = ANY(%s::uuid[])", (versions,))


def main() -> None:
    oidc_checks()
    cleanup()
    atexit.register(cleanup)
    author, lumen = login("cedar_auditor"), login("lumen_auditor")
    unique = str(uuid4())[:8]
    content = ("# Cedar controls\n## Invoice holds\nInvoice holds require finance approval before release.\n"
               "## Scope\nThis fictional policy applies to Cedar invoices.\n")
    status, _ = upload(author, "../outside.md", content.encode())
    assert status == 422
    status, _ = upload(author, f"v05-{unique}.md", b"\xff" * 20)
    assert status == 422
    status, _ = upload(author, f"v05-{unique}.md", b"A" * 32769)
    assert status == 413
    status, source = upload(author, f"v05-{unique}.md", content.encode())
    assert status == 201 and source["origin"] == f"upload:v05-{unique}.md", source
    status, _ = call("GET", f"/v1/sources/{source['source_id']}/versions", lumen)
    assert status == 404
    corrected = {"kind": "markdown", "origin": source["origin"],
                 "content": content.replace("fictional policy", "fictional Cedar policy"),
                 "valid_from": "2026-07-01", "permissions": ["auditor", "owner"]}
    status, source2 = mutate(f"/v1/sources/{source['source_id']}/versions", author, corrected, source["etag"])
    assert status == 201 and source2["version"] == 2
    long_chunks = chunk_source("markdown", "# Large\n" + "alpha beta gamma " * 230)
    assert len(long_chunks) > 2 and all(0 < item.end_char - item.start_char <= MAX_CHARS for item in long_chunks)
    with connect(load_settings().database_url) as connection:
        first = connection.execute("SELECT chunk_id, section_id, start_char, end_char, content_sha256 "
                                   "FROM source_chunks WHERE source_version_id = %s", (source["version_id"],)).fetchall()
        second = connection.execute("SELECT chunk_id, section_id FROM source_chunks WHERE source_version_id = %s",
                                    (source2["version_id"],)).fetchall()
    assert first and all(hashlib.sha256(content[row[2]:row[3]].encode()).hexdigest() == row[4].strip() for row in first)
    assert {row[0] for row in first if row[1].endswith("invoice-holds")} == {
        row[0] for row in second if row[1].endswith("invoice-holds")}

    snap_content = f"# Fictional connector\n## Invoice holds\nInvoice holds require finance approval for case {unique}."
    snapshot = {"remote_id": f"v05-{unique}", "remote_version": "r1",
                "sha256": hashlib.sha256(snap_content.encode()).hexdigest(),
                "source": {"kind": "markdown", "origin": "Fictional push source", "content": snap_content,
                           "valid_from": "2026-07-01", "permissions": ["auditor", "owner"]}}
    connector_path = "/v1/connectors/fictional-push/snapshots"
    status, pushed = mutate(connector_path, author, snapshot)
    assert status == 201 and pushed["version"] == 1
    status, duplicate = mutate(connector_path, author, snapshot)
    assert status == 201 and duplicate["version_id"] == pushed["version_id"]
    status, _ = mutate(connector_path, author, {**snapshot, "source": {**snapshot["source"], "permissions": ["auditor"]}})
    assert status == 409
    status, _ = mutate(connector_path, author, {**snapshot, "sha256": "0" * 64})
    assert status == 422
    status, _ = mutate("/v1/connectors/disabled/snapshots", author, snapshot)
    assert status == 403
    new_text = snap_content.replace("finance approval", "two finance approvals")
    next_snapshot = {**snapshot, "remote_version": "r2", "sha256": hashlib.sha256(new_text.encode()).hexdigest(),
                     "source": {**snapshot["source"], "content": new_text}}
    status, pushed2 = mutate(connector_path, author, next_snapshot)
    assert status == 201 and pushed2["version"] == 2 and pushed2["source_id"] == pushed["source_id"]
    status, _ = mutate(connector_path, author, {**snapshot, "source": {**snapshot["source"], "content": new_text},
                                                "sha256": hashlib.sha256(new_text.encode()).hexdigest()})
    assert status == 409
    cleanup()
    print("v0.5 intake/auth passed: strict OIDC tokens, bounded upload, connector revisions, tenant scope, and stable indexed chunks.")


if __name__ == "__main__":
    main()
