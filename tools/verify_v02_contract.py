"""Validate live v0.2 answer and source-detail responses against OpenAPI schemas."""

import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, headers: dict | None = None) -> dict:
    request = Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})}, method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


login = post("/demo/login", {"account": "cedar_auditor", "passphrase": "local-demo-only"})
token = login["access_token"]
answer = post(
    "/v1/query",
    {"question": "How many reviewers did Cedar overrides require on May 10?",
     "valid_on": "2026-05-10", "recorded_as_of": "2026-06-30T00:00:00Z", "answer_mode": "structured"},
    {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid4())},
)
schemas = SPEC["components"]["schemas"]
answer_schema = deepcopy(schemas["Answer"])
claim_schema = deepcopy(schemas["Claim"])
claim_schema["properties"]["citations"]["items"] = schemas["Citation"]
answer_schema["properties"]["claims"]["items"] = claim_schema
Draft202012Validator(answer_schema).validate(answer)
assert answer["claims"]
citation = answer["claims"][0]["citations"][0]
path = (f"/v1/sources/{citation['source_id']}/versions/{citation['version_id']}?"
        + urlencode({"recorded_as_of": answer["recorded_as_of"]}))
request = Request(BASE + path, headers={"Authorization": f"Bearer {token}"})
with urlopen(request, timeout=10) as response:
    source = json.load(response)
Draft202012Validator(schemas["SourceVersion"]).validate(source)
assert source["content"][citation["start_char"]:citation["end_char"]] == citation["quote"]
print("Live Answer and SourceVersion responses conform to OpenAPI schemas.")
