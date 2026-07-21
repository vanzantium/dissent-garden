from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .contracts import CorrectionRequest, DecisionRequest, DeliberationResult
from .engine import MODEL, deliberate
from .governor import TokenGovernor
from .ledger import AppendOnlyLedger
from .sample_data import SAMPLE_REQUEST, showcase_result


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
ledger = AppendOnlyLedger(ROOT / "data" / "decision_ledger.jsonl")
governor = TokenGovernor(ROOT / "data" / "governor_state.json")

app = FastAPI(title="Dissent Garden", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {
        "ok": True,
        "live_ready": bool(os.getenv("OPENAI_API_KEY")),
        "model": MODEL,
        "ledger": ledger.verify(),
        "governor": governor.status(),
    }


@app.get("/api/sample")
async def sample() -> dict[str, object]:
    return SAMPLE_REQUEST.model_dump()


def _record_result(
    result: DeliberationResult, request: DecisionRequest, request_fingerprint: str = ""
) -> DeliberationResult:
    record = ledger.append(
        "decision",
        {
            "decision_id": result.decision_id,
            "mode": result.mode,
            "model": result.model,
            "request_fingerprint": request_fingerprint or governor.fingerprint(request),
            "request": request.model_dump(),
            "result": result.model_dump(exclude={"receipt_hash"}),
        },
    )
    result.receipt_hash = record["record_hash"]
    return result


@app.post("/api/showcase", response_model=DeliberationResult)
async def showcase() -> DeliberationResult:
    return _record_result(showcase_result(), SAMPLE_REQUEST)


@app.post("/api/deliberate", response_model=DeliberationResult)
async def run_deliberation(request: DecisionRequest) -> DeliberationResult:
    plan = governor.plan(request, ledger.records())
    if plan.exact_record:
        source = plan.exact_record
        result = DeliberationResult.model_validate(source["payload"]["result"])
        result.mode = "reused"
        result.governor = governor.record(
            plan=plan,
            input_tokens=0,
            output_tokens=0,
            saved_tokens=plan.reuse_tokens_avoided,
            estimated_context_tokens_avoided=0,
            note=(
                "Exact decision and evidence match: reused a correction-free verified receipt "
                "without a GPT-5.6 call. Tokens avoided come from that receipt's actual usage."
            ),
        )
        result.governor.receipt_reused = source["record_hash"]
        reuse = ledger.append(
            "reuse",
            {
                "decision_id": result.decision_id,
                "source_receipt": source["record_hash"],
                "request_fingerprint": plan.fingerprint,
                "saved_tokens": plan.reuse_tokens_avoided,
            },
        )
        result.receipt_hash = reuse["record_hash"]
        return result
    try:
        result, usage = await deliberate(request, plan)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # SDK errors are normalized at the API boundary.
        body = getattr(exc, "body", None)
        response = getattr(exc, "response", None)
        response_detail = ""
        if response is not None:
            try:
                response_detail = json.dumps(response.json(), ensure_ascii=False)
            except Exception:
                response_detail = getattr(response, "text", "") or ""
        diagnostic_source = response_detail or (
            json.dumps(body, ensure_ascii=False) if body else str(exc)
        )
        diagnostic = " ".join(diagnostic_source.split())[:1000]
        raise HTTPException(
            status_code=502,
            detail=(
                f"GPT-5.6 deliberation failed: {type(exc).__name__}"
                + (f": {diagnostic}" if diagnostic else "")
            ),
        ) from exc
    result.governor = governor.record(
        plan=plan,
        input_tokens=usage[0],
        output_tokens=usage[1],
        saved_tokens=0,
        estimated_context_tokens_avoided=plan.estimated_context_tokens_avoided,
        note=(
            f"Consulted {plan.receipts_consulted} ranked receipt(s) in a bounded memory brief."
            if plan.receipts_consulted
            else "No prior receipt was relevant; ran a fresh bounded deliberation."
        ),
    )
    return _record_result(result, request, plan.fingerprint)


@app.get("/api/ledger")
async def list_ledger() -> dict[str, object]:
    return {"verification": ledger.verify(), "records": ledger.list()}


@app.get("/api/governor")
async def governor_status() -> dict[str, object]:
    return governor.status()


@app.post("/api/decisions/{decision_id}/corrections")
async def add_correction(decision_id: str, correction: CorrectionRequest) -> dict[str, object]:
    if not ledger.has_decision(decision_id):
        raise HTTPException(status_code=404, detail="Decision receipt not found")
    record = ledger.append(
        "correction", {"decision_id": decision_id, "note": correction.note}
    )
    return {"ok": True, "record": record, "verification": ledger.verify()}
