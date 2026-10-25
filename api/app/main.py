"""Readiness API and a clearly scoped synthetic historical-answer demo."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import re
from typing import Literal
from uuid import UUID, uuid4

import hmac
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, load_settings
from .db import is_ready
from .auth import ACCOUNTS, Actor, LoginRequest, issue_token, load_demo_credentials, require_actor
from .query import QueryRequest, open_evidence, query_with_idempotency
from .oidc import OidcConfig
from .workflow import (
    ConnectorSnapshot, DecisionDraft, ReviewAction, SourceCreate, append_source, create_decision,
    create_source, decision_history, list_decisions, list_sources,
    push_connector_snapshot, review_decision, source_history,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = load_settings()
    app.state.auth_mode = os.environ.get("AUTH_MODE", "demo").strip().lower()
    if app.state.auth_mode == "demo":
        app.state.demo_passphrase, app.state.demo_secret = load_demo_credentials()
    elif app.state.auth_mode == "oidc":
        app.state.oidc_config = OidcConfig(
            issuer=os.environ.get("OIDC_ISSUER", ""),
            audience=os.environ.get("OIDC_AUDIENCE", ""),
            jwks_url=os.environ.get("OIDC_JWKS_URL", ""),
            tenants=frozenset(item.strip() for item in os.environ.get("OIDC_ALLOWED_TENANTS", "").split(",") if item.strip()),
        )
    else:
        raise RuntimeError("AUTH_MODE must be demo or oidc")
    yield


app = FastAPI(title="DecisionTrace", version="0.5.0-preview", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if 1 <= len(supplied) <= 64 and supplied.replace("-", "").isalnum() else str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def problem(request: Request, status: int, code: str, title: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"urn:decisiontrace:problem:{code}",
            "title": title,
            "status": status,
            "code": code,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException):
    return problem(request, exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return problem(request, 422, "invalid_request", "Invalid request")


@app.get("/health/live")
def live():
    return {"status": "live"}


@app.get("/health/ready")
def ready(request: Request):
    settings: Settings = request.app.state.settings
    try:
        if is_ready(settings.database_url):
            return {"status": "ready"}
    except Exception:
        pass
    return problem(request, 503, "not_ready", "Database or schema unavailable")


@app.get("/version")
def version():
    return {"service": "decisiontrace", "version": "0.5.0-preview", "product_ready": False,
            "auth_mode": os.environ.get("AUTH_MODE", "demo").strip().lower()}


@app.get("/demo/accounts")
def demo_accounts():
    if os.environ.get("AUTH_MODE", "demo").strip().lower() != "demo":
        raise HTTPException(status_code=404, detail="Demo identities are disabled")
    return [{"account": actor.account, "tenant": actor.tenant, "role": actor.role} for actor in ACCOUNTS.values()]


@app.post("/demo/login")
def demo_login(login: LoginRequest, request: Request):
    if request.app.state.auth_mode != "demo":
        raise HTTPException(status_code=404, detail="Demo login is disabled")
    if login.account not in ACCOUNTS or not hmac.compare_digest(login.passphrase, request.app.state.demo_passphrase):
        raise HTTPException(status_code=401, detail="Invalid demo account or passphrase")
    actor = ACCOUNTS[login.account]
    return {
        "access_token": issue_token(actor.account, request.app.state.demo_secret),
        "token_type": "bearer", "expires_in": 8 * 3600,
        "account": actor.account, "tenant": actor.tenant, "role": actor.role,
    }


@app.get("/demo/session")
def demo_session(actor: Actor = Depends(require_actor)):
    return {"account": actor.account, "tenant": actor.tenant, "role": actor.role}


@app.get("/v1/session")
def current_session(actor: Actor = Depends(require_actor)):
    return {"account": actor.account, "tenant": actor.tenant, "role": actor.role}


@app.get("/v1/sources")
def get_sources(request: Request, actor: Actor = Depends(require_actor)):
    return list_sources(request.app.state.settings.database_url, actor)


@app.post("/v1/sources", status_code=201)
def post_source(
    body: SourceCreate, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    actor: Actor = Depends(require_actor),
):
    return create_source(request.app.state.settings.database_url, actor, body, idempotency_key)


@app.post("/v1/sources/upload", status_code=201)
async def upload_source(
    request: Request,
    kind: Literal["markdown", "transcript", "json"] = Query(),
    valid_from: str = Query(),
    permissions: str = Query(),
    filename: str = Header(alias="X-Source-Filename"),
    idempotency_key: str = Header(alias="Idempotency-Key"),
    actor: Actor = Depends(require_actor),
):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", filename) or ".." in filename:
        raise HTTPException(status_code=422, detail="Unsafe source filename")
    suffixes = {"markdown": (".md", ".txt"), "transcript": (".txt",), "json": (".json",)}
    if not filename.lower().endswith(suffixes[kind]):
        raise HTTPException(status_code=422, detail="Filename does not match source kind")
    if request.headers.get("Content-Type", "").split(";", 1)[0].lower() not in {
        "text/plain", "text/markdown", "application/json", "application/octet-stream",
    }:
        raise HTTPException(status_code=415, detail="Unsupported source media type")
    raw = bytearray()
    async for piece in request.stream():
        if len(raw) + len(piece) > 32768:
            raise HTTPException(status_code=413, detail="Source file exceeds 32 KiB")
        raw.extend(piece)
    try:
        content = raw.decode("utf-8", errors="strict")
        if "\x00" in content:
            raise ValueError("NUL byte")
        body = SourceCreate.model_validate({
            "kind": kind, "origin": f"upload:{filename}", "content": content,
            "valid_from": valid_from, "permissions": [part.strip() for part in permissions.split(",")],
        })
    except (UnicodeDecodeError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="Invalid UTF-8 source file or metadata") from exc
    return create_source(request.app.state.settings.database_url, actor, body, idempotency_key)


@app.post("/v1/connectors/{connector_id}/snapshots", status_code=201)
def post_connector_snapshot(
    connector_id: str, body: ConnectorSnapshot, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    actor: Actor = Depends(require_actor),
):
    allowed = frozenset(item.strip() for item in os.environ.get("CONNECTOR_IDS", "").split(",") if item.strip())
    return push_connector_snapshot(request.app.state.settings.database_url, actor, connector_id, body,
                                   idempotency_key, allowed)


@app.get("/v1/sources/{source_id}/versions")
def get_source_history(source_id: UUID, request: Request, actor: Actor = Depends(require_actor)):
    return source_history(request.app.state.settings.database_url, actor, source_id)


@app.post("/v1/sources/{source_id}/versions", status_code=201)
def post_source_version(
    source_id: UUID, body: SourceCreate, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    if_match: str = Header(alias="If-Match"),
    actor: Actor = Depends(require_actor),
):
    return append_source(request.app.state.settings.database_url, actor, source_id, body, if_match, idempotency_key)


@app.get("/v1/decision-contracts")
def get_decisions(request: Request, actor: Actor = Depends(require_actor)):
    return list_decisions(request.app.state.settings.database_url, actor)


@app.post("/v1/decision-contracts", status_code=201)
def post_decision(
    body: DecisionDraft, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    actor: Actor = Depends(require_actor),
):
    return create_decision(request.app.state.settings.database_url, actor, body, idempotency_key)


@app.post("/v1/decision-contracts/{decision_id}/review")
def post_decision_review(
    decision_id: UUID, body: ReviewAction, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    if_match: str = Header(alias="If-Match"),
    actor: Actor = Depends(require_actor),
):
    return review_decision(request.app.state.settings.database_url, actor, decision_id, body, if_match, idempotency_key)


@app.get("/v1/decision-contracts/{decision_id}/history")
def get_decision_history(decision_id: UUID, request: Request, actor: Actor = Depends(require_actor)):
    return decision_history(request.app.state.settings.database_url, actor, decision_id)


@app.post("/v1/query")
def query_evidence(
    query: QueryRequest, request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    actor: Actor = Depends(require_actor),
):
    settings: Settings = request.app.state.settings
    return query_with_idempotency(settings.database_url, actor, query, idempotency_key)


@app.get("/v1/sources/{source_id}/versions/{version_id}")
def get_source_version(
    source_id: UUID, version_id: UUID, request: Request,
    recorded_as_of: datetime = Query(), actor: Actor = Depends(require_actor),
):
    if recorded_as_of.tzinfo is None or recorded_as_of.utcoffset() is None:
        raise HTTPException(status_code=422, detail="recorded_as_of must include a timezone")
    settings: Settings = request.app.state.settings
    source = open_evidence(settings.database_url, actor, source_id, version_id, recorded_as_of.astimezone(timezone.utc))
    if source is None:
        raise HTTPException(status_code=404, detail="Source version not available")
    return source
