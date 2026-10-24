"""Readiness API and a clearly scoped synthetic historical-answer demo."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID, uuid4

import hmac
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, load_settings
from .db import is_ready
from .auth import ACCOUNTS, Actor, LoginRequest, issue_token, load_demo_credentials, require_actor
from .query import QueryRequest, open_evidence, query_with_idempotency


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = load_settings()
    app.state.demo_passphrase, app.state.demo_secret = load_demo_credentials()
    yield


app = FastAPI(title="DecisionTrace foundation", version="0.1.0-dev", lifespan=lifespan)


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
    return {"service": "decisiontrace", "version": "0.1.0-dev", "product_ready": False}


@app.get("/demo/accounts")
def demo_accounts():
    return [{"account": actor.account, "tenant": actor.tenant, "role": actor.role} for actor in ACCOUNTS.values()]


@app.post("/demo/login")
def demo_login(login: LoginRequest, request: Request):
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
