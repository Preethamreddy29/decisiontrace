"""Loopback-only, synthetic demo identities and signed bearer sessions.

These shared demo credentials are intentionally published with the fixture.
They let the API derive tenant and role from a server-verified token; they are
not a production identity provider.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class Actor:
    account: str
    tenant: str
    role: str


def actor_scope(actor: Actor) -> str:
    """Keep idempotent responses separate across tenant and role changes."""
    return f"{actor.tenant}\x1f{actor.role}\x1f{actor.account}"


ACCOUNTS = {
    "cedar_auditor": Actor("cedar_auditor", "cedar", "auditor"),
    "cedar_reviewer": Actor("cedar_reviewer", "cedar", "auditor"),
    "cedar_viewer": Actor("cedar_viewer", "cedar", "viewer"),
    "lumen_auditor": Actor("lumen_auditor", "lumen", "auditor"),
}


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account: str = Field(min_length=3, max_length=64)
    passphrase: str = Field(min_length=1, max_length=128)


def load_demo_credentials() -> tuple[str, bytes]:
    passphrase = os.environ.get("DEMO_PASSPHRASE", "")
    if not passphrase:
        raise RuntimeError("DEMO_PASSPHRASE is required")
    secret = secrets.token_bytes(32)  # Restart invalidates local demo sessions.
    return passphrase, secret


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(account: str, secret: bytes) -> str:
    payload = {"account": account, "expires": int(time.time()) + 8 * 3600}
    body = _b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signature = _b64encode(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_token(token: str, secret: bytes) -> Actor:
    try:
        body, signature = token.split(".", 1)
        if len(body) > 512 or len(signature) > 128:
            raise ValueError("oversized token")
        expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(body))
        if not isinstance(payload, dict) or not isinstance(payload.get("expires"), int):
            raise ValueError("bad payload")
        if payload["expires"] <= int(time.time()):
            raise ValueError("expired")
        actor = ACCOUNTS.get(payload.get("account"))
        if actor is None:
            raise ValueError("unknown account")
        return actor
    except (ValueError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, binascii.Error) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired demo session") from exc


def require_actor(request: Request) -> Actor:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer access token required")
    if request.app.state.auth_mode == "oidc":
        from .oidc import verify_oidc_token
        return verify_oidc_token(token, request.app.state.oidc_config)
    return verify_token(token, request.app.state.demo_secret)
