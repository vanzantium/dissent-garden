from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts import DecisionRequest, EvidenceItem
from app.ledger import AppendOnlyLedger
from app.main import app
from app.governor import TokenGovernor
from app import engine


main_module = importlib.import_module("app.main")
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch, tmp_path: Path) -> None:
    """Keep automated tests from reading or writing the real demo ledger."""
    monkeypatch.setattr(
        main_module, "ledger", AppendOnlyLedger(tmp_path / "decision_ledger.jsonl")
    )
    monkeypatch.setattr(
        main_module, "governor", TokenGovernor(tmp_path / "governor_state.json")
    )


def test_health_and_front_door() -> None:
    assert client.get("/").status_code == 200
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["model"] == "gpt-5.6-sol"


def test_showcase_is_complete() -> None:
    response = client.post("/api/showcase")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "showcase"
    assert len(payload["seats"]) == 3
    assert {claim["status"] for claim in payload["claims"]} == {
        "survived",
        "disputed",
        "unsupported",
    }
    assert payload["claim_survival_rate"] == 0.6
    assert len(payload["receipt_hash"]) == 64


def test_live_route_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sample = client.get("/api/sample").json()
    response = client.post("/api/deliberate", json=sample)
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_duplicate_evidence_ids_rejected() -> None:
    try:
        DecisionRequest(
            question="Should we run this bounded product experiment now?",
            evidence=[
                EvidenceItem(id="E1", title="One", content="First fact"),
                EvidenceItem(id="E1", title="Two", content="Second fact"),
            ],
        )
    except ValueError as exc:
        assert "unique" in str(exc).lower()
    else:
        raise AssertionError("duplicate evidence IDs were accepted")


def test_ledger_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = AppendOnlyLedger(path)
    ledger.append("decision", {"decision_id": "DG-TEST", "decision": "Proceed"})
    ledger.append("correction", {"decision_id": "DG-TEST", "note": "New evidence"})
    assert ledger.verify()["valid"] is True

    records = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(records[0])
    first["payload"]["decision"] = "Tampered"
    records[0] = json.dumps(first)
    path.write_text("\n".join(records) + "\n", encoding="utf-8")
    assert ledger.verify()["valid"] is False


def test_governor_reuses_only_live_verified_receipts(tmp_path: Path) -> None:
    governor = TokenGovernor(tmp_path / "governor.json")
    request = DecisionRequest(
        question="Should the product team replace its weekly planning meeting?",
        context="The team wants more focus time.",
        evidence=[EvidenceItem(id="E1", title="Time", content="Meetings take four hours")],
    )
    result = client.post("/api/showcase").json()
    result["governor"]["input_tokens"] = 1200
    result["governor"]["output_tokens"] = 300
    base_payload = {
        "request": request.model_dump(),
        "request_fingerprint": governor.fingerprint(request),
        "result": result,
    }
    showcase = {
        "kind": "decision",
        "record_hash": "a" * 64,
        "payload": {**base_payload, "mode": "showcase"},
    }
    assert governor.plan(request, [showcase]).exact_record is None

    live = {
        "kind": "decision",
        "record_hash": "b" * 64,
        "payload": {**base_payload, "mode": "live"},
    }
    plan = governor.plan(request, [showcase, live])
    assert plan.exact_record == live
    assert plan.reuse_tokens_avoided == 1500


def test_correction_invalidates_exact_reuse_and_enters_memory(tmp_path: Path) -> None:
    governor = TokenGovernor(tmp_path / "governor.json")
    request = DecisionRequest(
        question="Should the product team release this workflow change on Monday?",
        context="A reversible stage is available.",
    )
    live = {
        "kind": "decision",
        "record_hash": "d" * 64,
        "payload": {
            "mode": "live",
            "decision_id": "DG-CORRECTED",
            "request": request.model_dump(),
            "request_fingerprint": governor.fingerprint(request),
            "result": {
                "decision": "Run the stage",
                "unresolved_tension": "Speed versus reliability",
                "next_test": "Measure errors",
                "governor": {"input_tokens": 900, "output_tokens": 300},
            },
        },
    }
    correction = {
        "kind": "correction",
        "record_hash": "e" * 64,
        "payload": {
            "decision_id": "DG-CORRECTED",
            "note": "The error rate doubled after the first hour.",
        },
    }
    plan = governor.plan(request, [live, correction])
    assert plan.exact_record is None
    assert "error rate doubled" in plan.memory_brief


def test_fingerprint_ignores_whitespace_and_constraint_order(tmp_path: Path) -> None:
    governor = TokenGovernor(tmp_path / "governor.json")
    left = DecisionRequest(
        question="Should we stage the release on Monday?",
        context="The team needs a reversible test.",
        constraints=["No weekend release", "Rollback under 30 minutes"],
    )
    right = DecisionRequest(
        question="  Should   we stage the release on Monday?  ",
        context="The team needs a reversible test.",
        constraints=["Rollback under 30 minutes", "No weekend release"],
    )
    assert governor.fingerprint(left) == governor.fingerprint(right)


def test_governor_compacts_relevant_receipts_and_records_savings(tmp_path: Path) -> None:
    governor = TokenGovernor(tmp_path / "governor.json")
    old_request = DecisionRequest(
        question="Should our product team replace the weekly status meeting?",
        context="We want focus time.",
    )
    current = DecisionRequest(
        question="Should our product team shorten the weekly status meeting?",
        context="We want more focus time without hiding blockers.",
    )
    receipt = {
        "kind": "decision",
        "record_hash": "c" * 64,
        "payload": {
            "mode": "live",
            "request": old_request.model_dump(),
            "result": {
                "decision": "Run a trial",
                "unresolved_tension": "Focus versus awareness",
                "next_test": "Measure blocker acknowledgement time",
            },
        },
    }
    plan = governor.plan(current, [receipt])
    assert plan.exact_record is None
    assert plan.receipts_consulted == 1
    assert len(plan.memory_brief) <= 1800
    report = governor.record(
        plan=plan,
        input_tokens=1200,
        output_tokens=400,
        saved_tokens=0,
        estimated_context_tokens_avoided=plan.estimated_context_tokens_avoided,
        note="test",
    )
    assert report.input_tokens == 1200
    assert governor.status()["daily_used_tokens"] == 1600


def test_live_pipeline_uses_four_structured_calls(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class Usage:
        input_tokens = 10
        output_tokens = 20

    class Response:
        def __init__(self, payload: dict) -> None:
            self.output_text = json.dumps(payload)
            self.output_parsed = None
            self.usage = Usage()

    class Responses:
        async def parse(self, **kwargs):
            name = kwargs["metadata"]["dissent_stage"]
            calls.append(name)
            if name.endswith("_pass"):
                response = Response(
                    {
                        "thesis": "A sufficiently detailed independent thesis for the test.",
                        "claims": [
                            {"statement": "Evidence supports a bounded trial.", "evidence_ids": ["E1"], "confidence": 0.9},
                            {"statement": "The outcome remains uncertain.", "evidence_ids": [], "confidence": 0.6},
                        ],
                        "question_for_others": "What result would reverse this decision?",
                    }
                )
                response.output_parsed = engine.SeatCallResult.model_validate(
                    json.loads(response.output_text)
                )
                return response
            response = Response(
                {
                    "claims": [
                        {"id": "C1", "statement": "A bounded trial is supported.", "status": "survived", "evidence_ids": ["E1"], "supporting_seats": ["builder", "grounder"], "challenge": "The sample is small."},
                        {"id": "C2", "statement": "The result is guaranteed.", "status": "unsupported", "evidence_ids": [], "supporting_seats": ["builder"], "challenge": "No guarantee was supplied."},
                        {"id": "C3", "statement": "The trial may hide weak signals.", "status": "disputed", "evidence_ids": ["E1"], "supporting_seats": ["breaker"], "challenge": "The risk is plausible but unmeasured."},
                    ],
                    "surviving_core": "The supplied evidence supports a small reversible test.",
                    "unresolved_tension": "Efficiency may trade away ambient awareness.",
                    "next_test": "Run the change for one week and measure acknowledgement time.",
                    "decision": "Proceed with a one-week reversible test.",
                }
            )
            response.output_parsed = engine.ArbiterCallResult.model_validate(
                json.loads(response.output_text)
            )
            return response

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            self.responses = Responses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(engine, "AsyncOpenAI", FakeClient)
    request = DecisionRequest(
        question="Should this team run a small reversible workflow trial?",
        evidence=[EvidenceItem(id="E1", title="Observation", content="The workflow consumes four hours")],
    )
    plan = TokenGovernor(tmp_path / "governor.json").plan(request, [])
    result, usage = asyncio.run(engine.deliberate(request, plan))
    assert calls == ["builder_pass", "breaker_pass", "grounder_pass", "dissent_garden_verdict"]
    assert usage == (40, 80)
    assert result.mode == "live"
    assert result.claim_survival_rate == 0.333


def test_correction_requires_existing_decision() -> None:
    response = client.post(
        "/api/decisions/DG-DOES-NOT-EXIST/corrections",
        json={"note": "This should not create an orphan correction."},
    )
    assert response.status_code == 404
