"""Strict OIDC access-token verification for the optional external identity mode."""

import json
import re
import threading
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import jwt
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from .auth import Actor


@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    audience: str
    jwks_url: str
    tenants: frozenset[str]

    def __post_init__(self):
        issuer = urlparse(self.issuer)
        keys = urlparse(self.jwks_url)
        if issuer.scheme != "https" or not issuer.netloc or keys.scheme != "https" or not keys.netloc:
            raise RuntimeError("OIDC issuer and JWKS URL must use HTTPS")
        if not self.audience or not self.tenants or any(not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", item) for item in self.tenants):
            raise RuntimeError("OIDC audience and allowed tenants are required")


_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}


def fetch_jwks(config: OidcConfig, refresh: bool = False) -> dict:
    with _lock:
        cached = _cache.get(config.jwks_url)
        if cached and cached[0] > time.monotonic() and not refresh:
            return cached[1]
        try:
            request = Request(config.jwks_url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=3) as response:
                if response.url != config.jwks_url or response.status != 200:
                    raise ValueError("unexpected JWKS response")
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("oversized JWKS")
            document = json.loads(raw)
            if not isinstance(document, dict) or not isinstance(document.get("keys"), list) or len(document["keys"]) > 32:
                raise ValueError("invalid JWKS")
        except (URLError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=503, detail="Identity keys unavailable") from exc
        _cache[config.jwks_url] = (time.monotonic() + 300, document)
        return document


def verify_oidc_token(token: str, config: OidcConfig, jwks: dict | None = None) -> Actor:
    try:
        if len(token) > 8192:
            raise ValueError("oversized token")
        header = jwt.get_unverified_header(token)
        if (header.get("alg") != "RS256" or not isinstance(header.get("kid"), str)
                or len(header["kid"]) > 128 or "crit" in header):
            raise ValueError("unexpected token header")
        document = jwks if jwks is not None else fetch_jwks(config)
        matches = [item for item in document.get("keys", []) if isinstance(item, dict) and item.get("kid") == header["kid"]]
        if not matches and jwks is None:
            matches = [item for item in fetch_jwks(config, refresh=True).get("keys", [])
                       if isinstance(item, dict) and item.get("kid") == header["kid"]]
        if len(matches) != 1:
            raise ValueError("unknown or duplicate key")
        jwk = matches[0]
        if (jwk.get("kty") != "RSA" or jwk.get("use", "sig") != "sig"
                or jwk.get("alg", "RS256") != "RS256"
                or ("key_ops" in jwk and "verify" not in jwk["key_ops"])):
            raise ValueError("invalid signing key")
        key = RSAAlgorithm.from_jwk(json.dumps(jwk))
        if key.key_size < 2048:
            raise ValueError("signing key is too short")
        claims = jwt.decode(
            token, key=key, algorithms=["RS256"], issuer=config.issuer, audience=config.audience,
            options={"require": ["iss", "aud", "sub", "exp", "iat"]}, leeway=30,
        )
        tenant, role, subject = claims.get("tenant"), claims.get("role"), claims.get("sub")
        if tenant not in config.tenants or role not in {"owner", "engineer", "qa", "auditor", "viewer"}:
            raise ValueError("unauthorized tenant or role")
        if not isinstance(subject, str) or not 1 <= len(subject) <= 256:
            raise ValueError("invalid subject")
        return Actor(account=f"{config.issuer}|{subject}", tenant=tenant, role=role)
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc
