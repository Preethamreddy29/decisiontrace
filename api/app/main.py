"""Readiness API and a clearly scoped synthetic historical-answer demo."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, load_settings
from .db import is_ready
from .demo import DemoQuery, answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = load_settings()
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


@app.post("/demo/query")
def demo_query(query: DemoQuery, request: Request):
    settings: Settings = request.app.state.settings
    return answer(settings.database_url, query)
