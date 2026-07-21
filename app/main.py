from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .contracts import (
    CorrectionRequest,
    DecisionRequest,
    DeliberationResult,
    SeedCheckRequest,
    SeedCreate,
    SeedEvidenceCreate,
    SeedSimulationRequest,
)
from .engine import MODEL, deliberate
from .governor import TokenGovernor
from .ledger import AppendOnlyLedger
from .sample_data import SAMPLE_REQUEST, showcase_result
from .seeds import SeedRegistry, simulate_growth


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
DATA_DIR = Path(os.getenv("DISSENT_GARDEN_DATA_DIR", str(ROOT / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
ledger = AppendOnlyLedger(DATA_DIR / "decision_ledger.jsonl")
governor = TokenGovernor(DATA_DIR / "governor_state.json")
seed_registry = SeedRegistry(DATA_DIR / "seed_ledger.jsonl")
SEED_AUTOPILOT_SECONDS = max(
    15, int(os.getenv("DISSENT_GARDEN_SEED_AUTOPILOT_SECONDS", "60"))
)


async def _seed_autopilot() -> None:
    while True:
        await asyncio.sleep(SEED_AUTOPILOT_SECONDS)
        for seed in seed_registry.due():
            try:
                if seed["status"] == "sprouting":
                    if os.getenv("OPENAI_API_KEY"):
                        await _execute_deliberation(
                            seed_registry.decision_request(seed["seed_id"]),
                            seed_id=seed["seed_id"],
                        )
                    continue
                assessment = seed_registry.check(seed["seed_id"])
                if assessment.should_wake and os.getenv("OPENAI_API_KEY"):
                    await _execute_deliberation(
                        seed_registry.decision_request(seed["seed_id"]),
                        seed_id=seed["seed_id"],
                    )
            except Exception as exc:
                seed_registry.ledger.append(
                    "seed_autopilot_error",
                    {
                        "seed_id": seed["seed_id"],
                        "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    },
                )


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_seed_autopilot())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Dissent Garden", version="1.0.0", lifespan=lifespan)
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
        "seeds": {
            "active": len(
                [
                    seed
                    for seed in seed_registry.list()
                    if seed["status"] not in {"harvested", "shed"}
                ]
            ),
            "ledger": seed_registry.verify(),
            "autopilot_seconds": SEED_AUTOPILOT_SECONDS,
        },
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


def _provider_error(exc: Exception) -> HTTPException:
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
    return HTTPException(
        status_code=502,
        detail=(
            f"GPT-5.6 deliberation failed: {type(exc).__name__}"
            + (f": {diagnostic}" if diagnostic else "")
        ),
    )


async def _execute_deliberation(
    request: DecisionRequest, seed_id: str = ""
) -> DeliberationResult:
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
            model=MODEL,
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
        if seed_id:
            seed_registry.bloom(seed_id, result.decision_id, result.receipt_hash)
        return result

    forecast = governor.forecast(request, plan, MODEL)
    seed_admission = None
    if seed_id:
        seed_admission = seed_registry.reserve(seed_id, forecast.cost_usd)
        if not seed_admission.allowed:
            raise HTTPException(status_code=402, detail=seed_admission.reason)
    admission = governor.reserve(request, plan, MODEL)
    if not admission.allowed:
        if seed_admission:
            seed_registry.release(
                seed_id, seed_admission.reservation_id, "Global Governor denied call."
            )
        raise HTTPException(status_code=429, detail=admission.reason)
    try:
        result, usage = await deliberate(request, plan)
    except RuntimeError as exc:
        governor.release(admission.reservation_id)
        if seed_admission:
            seed_registry.release(
                seed_id, seed_admission.reservation_id, "Call did not reach provider."
            )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # SDK errors are normalized at the API boundary.
        governor.forfeit(
            admission.reservation_id,
            "Provider outcome was uncertain; reserved ceiling charged to fail closed.",
        )
        if seed_admission:
            seed_registry.settle(
                seed_id,
                seed_admission.reservation_id,
                seed_admission.reserved_usd,
                outcome="provider outcome uncertain",
            )
        raise _provider_error(exc) from exc
    result.governor = governor.record(
        plan=plan,
        input_tokens=usage[0],
        output_tokens=usage[1],
        saved_tokens=0,
        estimated_context_tokens_avoided=plan.estimated_context_tokens_avoided,
        reservation_id=admission.reservation_id,
        model=MODEL,
        note=(
            f"Consulted {plan.receipts_consulted} ranked receipt(s) in a bounded memory brief."
            if plan.receipts_consulted
            else "No prior receipt was relevant; ran a fresh bounded deliberation."
        ),
    )
    result = _record_result(result, request, plan.fingerprint)
    if seed_admission:
        seed_registry.settle(
            seed_id,
            seed_admission.reservation_id,
            result.governor.actual_cost_usd,
        )
        seed_registry.bloom(seed_id, result.decision_id, result.receipt_hash)
    return result


@app.post("/api/deliberate", response_model=DeliberationResult)
async def run_deliberation(request: DecisionRequest) -> DeliberationResult:
    return await _execute_deliberation(request)


@app.get("/api/ledger")
async def list_ledger() -> dict[str, object]:
    return {"verification": ledger.verify(), "records": ledger.list()}


@app.get("/api/governor")
async def governor_status() -> dict[str, object]:
    return governor.status()


@app.get("/api/seeds")
async def list_seeds() -> dict[str, object]:
    return {"verification": seed_registry.verify(), "seeds": seed_registry.list()}


@app.post("/api/seeds")
async def plant_seed(request: SeedCreate) -> dict[str, object]:
    return {"ok": True, "seed": seed_registry.plant(request)}


@app.get("/api/seeds/{seed_id}")
async def get_seed(seed_id: str) -> dict[str, object]:
    seed = seed_registry.get(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    return {"seed": seed, "assessment": seed_registry.assess(seed_id).model_dump()}


@app.post("/api/seeds/{seed_id}/evidence")
async def add_seed_evidence(
    seed_id: str, update: SeedEvidenceCreate
) -> dict[str, object]:
    if not seed_registry.get(seed_id):
        raise HTTPException(status_code=404, detail="Seed not found")
    seed, added = seed_registry.add_evidence(seed_id, update)
    if seed and seed["status"] in {"harvested", "shed"}:
        raise HTTPException(status_code=409, detail="Seed is no longer active")
    return {
        "ok": True,
        "added": added,
        "seed": seed,
        "assessment": seed_registry.assess(seed_id).model_dump(),
    }


@app.post("/api/seeds/{seed_id}/check")
async def check_seed(
    seed_id: str, request: SeedCheckRequest
) -> dict[str, object]:
    if not seed_registry.get(seed_id):
        raise HTTPException(status_code=404, detail="Seed not found")
    assessment = seed_registry.check(seed_id)
    result = None
    if request.run_model and assessment.should_wake:
        result = await _execute_deliberation(
            seed_registry.decision_request(seed_id), seed_id=seed_id
        )
    return {
        "ok": True,
        "assessment": assessment.model_dump(),
        "seed": seed_registry.get(seed_id),
        "result": result,
    }


@app.post("/api/seeds/{seed_id}/harvest")
async def harvest_seed(seed_id: str) -> dict[str, object]:
    seed = seed_registry.harvest(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    return {"ok": True, "seed": seed}


@app.post("/api/seeds/simulate")
async def simulate_seed(request: SeedSimulationRequest) -> dict[str, object]:
    return {
        "ok": True,
        "simulation": simulate_growth(
            days=request.days,
            budget_usd=request.budget_usd,
            material_every_days=request.material_every_days,
        ),
    }


@app.post("/api/decisions/{decision_id}/corrections")
async def add_correction(decision_id: str, correction: CorrectionRequest) -> dict[str, object]:
    if not ledger.has_decision(decision_id):
        raise HTTPException(status_code=404, detail="Decision receipt not found")
    record = ledger.append(
        "correction", {"decision_id": decision_id, "note": correction.note}
    )
    return {"ok": True, "record": record, "verification": ledger.verify()}
