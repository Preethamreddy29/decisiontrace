"""Live adversarial checks for the bounded exact-citation gate."""

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from api.app.auth import Actor
from api.app.config import load_settings
from api.app.db import connect
from api.app.query import QueryRequest, query_with_idempotency, resolve
from api.app.seed import stable_id
from api.app.verification import VERSION, verify_answer
from tools.eval_v03 import login, mutate


def main() -> None:
    database_url = load_settings().database_url
    cedar = Actor("cedar_auditor", "cedar", "auditor")
    question = "How many reviewers did Cedar overrides require on May 10?"
    request = QueryRequest(question=question, valid_on=date(2026, 5, 10),
                           recorded_as_of=datetime(2026, 5, 10, 23, 59, 59, tzinfo=timezone.utc))
    answer = resolve(database_url, cedar, request)
    assert answer["status"] == "answered" and verify_answer(database_url, cedar, request, answer)
    assert not verify_answer(database_url, Actor("lumen_auditor", "lumen", "auditor"), request, answer)

    def rejected(label: str, edit) -> None:
        forged = deepcopy(answer)
        edit(forged)
        assert not verify_answer(database_url, cedar, request, forged), label

    rejected("invented version", lambda value: value["claims"][0]["citations"][0].update(
        version_id=str(uuid4())))
    rejected("invented source", lambda value: value["claims"][0]["citations"][0].update(
        source_id=str(uuid4())))
    rejected("wrong section", lambda value: value["claims"][0]["citations"][0].update(
        section_id="not-a-section"))
    rejected("wrong offset", lambda value: value["claims"][0]["citations"][0].update(
        start_char=value["claims"][0]["citations"][0]["start_char"] + 1))
    rejected("wrong label", lambda value: value["claims"][0]["citations"][0].update(
        label="SRC-FAKE-v1"))
    rejected("unsupported claim", lambda value: value["claims"][0].update(
        text="Manual overrides require nine reviewers."))
    rejected("missing citation", lambda value: value["claims"][0].update(citations=[]))
    rejected("unapproved decision", lambda value: value["claims"][0].update(
        decision_version_id=str(uuid4())))
    rejected("revoked version", lambda value: value["claims"][0]["citations"][0].update(
        version_id=str(stable_id("version/SRC-REVOKED-001-v1")),
        source_id=str(stable_id("source/SRC-REVOKED-001"))))
    rejected("other tenant", lambda value: value["claims"][0]["citations"][0].update(
        version_id=str(stable_id("version/SRC-ADR-002-v1")),
        source_id=str(stable_id("source/SRC-ADR-002"))))

    early = request.model_copy(update={
        "recorded_as_of": datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
    })
    early_answer = deepcopy(answer)
    early_answer["recorded_as_of"] = early.recorded_as_of.isoformat()
    assert not verify_answer(database_url, cedar, early, early_answer), "future-recorded evidence"

    before_valid = request.model_copy(update={"valid_on": date(2026, 4, 29)})
    before_answer = deepcopy(answer)
    before_answer["valid_on"] = before_valid.valid_on.isoformat()
    assert not verify_answer(database_url, cedar, before_valid, before_answer), "wrong valid date"

    forged = deepcopy(answer)
    forged["claims"][0]["text"] = "Manual overrides require nine reviewers."
    gate_key = f"verifier-gate-{uuid4()}"
    replay_key = f"verifier-replay-{uuid4()}"
    try:
        with patch("api.app.query.resolve", return_value=forged):
            gated = query_with_idempotency(database_url, cedar, request, gate_key)
        assert gated["status"] == "abstain" and gated["claims"] == [], gated
        assert gated["pipeline_versions"]["verification"] == VERSION

        token = login("cedar_auditor")
        payload = request.model_dump(mode="json")
        status, live = mutate("/v1/query", token, payload, key=replay_key)
        assert status == 200 and live["status"] == "answered", live
        assert live["pipeline_versions"]["verification"] == VERSION
        tampered = deepcopy(live)
        tampered["claims"][0]["text"] = "Manual overrides require nine reviewers."
        with connect(database_url) as connection:
            connection.execute(
                "UPDATE query_requests SET answer = %s::jsonb WHERE idempotency_key = %s",
                (json.dumps(tampered), replay_key),
            )
        status, _ = mutate("/v1/query", token, payload, key=replay_key)
        assert status == 409, "tampered cached answer was replayed"
    finally:
        with connect(database_url) as connection:
            connection.execute(
                "DELETE FROM query_requests WHERE idempotency_key IN (%s, %s)",
                (gate_key, replay_key),
            )
    print("Exact citation gate passed: authorized quote, forged source/time/claim rejection, "
          "fresh-answer abstention and cached-answer denial.")


if __name__ == "__main__":
    main()
