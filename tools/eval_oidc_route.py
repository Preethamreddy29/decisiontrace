"""Exercise OIDC mode through real HTTP routes with a synthetic signing key."""

import base64
import json
import os
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa

from api.app import oidc
from api.app.config import load_settings
from api.app.db import connect


def encoded_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def request(base: str, method: str, path: str, token: str | None = None,
            body: dict | None = None, idempotency_key: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "POST":
        headers["Idempotency-Key"] = idempotency_key or str(uuid4())
    message = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method=method)
    try:
        with urlopen(message, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def main() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = key.public_key().public_numbers()
    jwks = {"keys": [{"kty": "RSA", "use": "sig", "alg": "RS256", "kid": "local-route-key",
                      "n": encoded_int(numbers.n), "e": encoded_int(numbers.e)}]}
    issuer = "https://synthetic-issuer.example.test"
    os.environ.update({"AUTH_MODE": "oidc", "OIDC_ISSUER": issuer,
                       "OIDC_AUDIENCE": "decisiontrace-api",
                       "OIDC_JWKS_URL": issuer + "/jwks.json",
                       "OIDC_ALLOWED_TENANTS": "cedar,lumen"})
    # The route uses the normal verifier. Only the key-fetch boundary is
    # supplied by this synthetic fixture; a real issuer remains an external gate.
    oidc.fetch_jwks = lambda config, refresh=False: jwks
    from api.app.main import app

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                           log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    query_key = str(uuid4())
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started, "OIDC API did not start"

        now = int(time.time())
        claims = {"iss": issuer, "aud": "decisiontrace-api", "sub": "external-author",
                  "tenant": "cedar", "role": "auditor", "iat": now, "exp": now + 300}
        def signed(payload: dict) -> str:
            return jwt.encode(payload, key, algorithm="RS256", headers={"kid": "local-route-key"})

        token = signed(claims)
        assert request(base, "GET", "/version")[1]["auth_mode"] == "oidc"
        assert request(base, "GET", "/v1/session")[0] == 401
        status, identity = request(base, "GET", "/v1/session", token)
        assert status == 200 and identity == {"account": issuer + "|external-author",
                                              "tenant": "cedar", "role": "auditor"}
        assert request(base, "GET", "/demo/accounts")[0] == 404
        assert request(base, "GET", "/demo/session")[0] == 404
        assert request(base, "GET", "/demo/session", token)[0] == 404
        assert request(base, "POST", "/demo/login", body={"account": "cedar_auditor",
                                                            "passphrase": "local-demo-only"})[0] == 404
        for claim_change in ({"aud": "another-api"}, {"tenant": "unknown"},
                             {"role": "admin"}, {"exp": now - 100}):
            assert request(base, "GET", "/v1/session", signed({**claims, **claim_change}))[0] == 401
        assert request(base, "GET", "/v1/sources", token)[0] == 200
        status, answer = request(base, "POST", "/v1/query", token, {
            "question": "How many reviewers did Cedar overrides require on May 10?",
            "valid_on": "2026-05-10", "recorded_as_of": "2026-05-10T23:59:59Z",
            "answer_mode": "structured",
        }, idempotency_key=query_key)
        assert status == 200 and answer["status"] == "answered" and answer["claims"], answer
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        with connect(load_settings().database_url) as connection:
            connection.execute("DELETE FROM query_requests WHERE idempotency_key = %s", (query_key,))
    print("OIDC route passed: verified identity, disabled demo endpoints, invalid claims, authorized query.")


if __name__ == "__main__":
    main()
