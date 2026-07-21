from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import DecisionRequest, GovernorReport


WORD = re.compile(r"[a-z0-9]{3,}")
MODEL_PRICING_USD_PER_MILLION = {
    "gpt-5.6": (5.0, 30.0),
    "gpt-5.6-sol": (5.0, 30.0),
    "gpt-5.6-terra": (2.5, 15.0),
    "gpt-5.6-luna": (1.0, 6.0),
}


@dataclass
class GovernorPlan:
    mode: str
    fingerprint: str
    memory_brief: str
    receipts_consulted: int
    reuse_tokens_avoided: int
    estimated_context_tokens_avoided: int
    seat_output_cap: int
    arbiter_output_cap: int
    exact_record: dict[str, Any] | None = None


@dataclass
class CostForecast:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass
class BudgetAdmission:
    allowed: bool
    reservation_id: str
    forecast: CostForecast
    reason: str


class TokenGovernor:
    """Receipt-aware context and token governor.

    It never rewrites history. Exact repeats reuse a verified prior result;
    near-relevant receipts are ranked and compressed into a bounded brief.
    """

    def __init__(self, path: Path, daily_budget: int | None = None) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.daily_budget = daily_budget or int(
            os.getenv("DISSENT_GARDEN_DAILY_TOKEN_BUDGET", "100000")
        )

    @staticmethod
    def _today() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d")

    def _state(self) -> dict[str, Any]:
        default = {
            "day": self._today(),
            "daily_budget_tokens": self.daily_budget,
            "daily_used_tokens": 0,
            "daily_saved_tokens": 0,
            "daily_estimated_context_tokens_avoided": 0,
            "daily_spent_usd": 0.0,
            "lifetime_used_tokens": 0,
            "lifetime_saved_tokens": 0,
            "lifetime_spent_usd": 0.0,
            "active_reservations": {},
            "events": [],
        }
        if not self.path.exists():
            return default
        try:
            state = {**default, **json.loads(self.path.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError):
            return default
        if state.get("day") != self._today():
            state.update(
                day=self._today(),
                daily_used_tokens=0,
                daily_saved_tokens=0,
                daily_estimated_context_tokens_avoided=0,
                daily_spent_usd=0.0,
                active_reservations={},
                events=[],
            )
        if state.get("daily_used_tokens", 0) and not state.get("daily_spent_usd", 0):
            inferred = sum(
                self.cost_usd(
                    int(event.get("input_tokens", 0)),
                    int(event.get("output_tokens", 0)),
                    event.get("model", "gpt-5.6-sol"),
                )
                for event in state.get("events", [])
            )
            state["daily_spent_usd"] = round(inferred, 6)
            if not state.get("lifetime_spent_usd", 0):
                state["lifetime_spent_usd"] = round(inferred, 6)
            state["spend_usd_inferred_from_legacy_events"] = True
        return state

    def _save(self, state: dict[str, Any]) -> None:
        state["events"] = state.get("events", [])[-100:]
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temp.replace(self.path)

    @staticmethod
    def estimate(text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def cost_usd(input_tokens: int, output_tokens: int, model: str) -> float:
        default_input, default_output = MODEL_PRICING_USD_PER_MILLION.get(
            model, (5.0, 30.0)
        )
        input_rate = float(
            os.getenv("DISSENT_GARDEN_INPUT_USD_PER_MILLION", str(default_input))
        )
        output_rate = float(
            os.getenv("DISSENT_GARDEN_OUTPUT_USD_PER_MILLION", str(default_output))
        )
        return round(
            max(0, input_tokens) * input_rate / 1_000_000
            + max(0, output_tokens) * output_rate / 1_000_000,
            6,
        )

    def forecast(
        self, request: DecisionRequest, plan: GovernorPlan, model: str
    ) -> CostForecast:
        """Conservative preflight ceiling for the four-call pipeline."""
        if plan.exact_record:
            return CostForecast(0, 0, 0, 0.0)
        request_tokens = self.estimate(
            json.dumps(request.model_dump(), ensure_ascii=False, sort_keys=True)
        )
        memory_tokens = self.estimate(plan.memory_brief) if plan.memory_brief else 0
        seat_inputs = 3 * (request_tokens + 600)
        arbiter_input = (
            request_tokens + memory_tokens + (3 * plan.seat_output_cap) + 900
        )
        input_ceiling = seat_inputs + arbiter_input
        output_ceiling = (3 * plan.seat_output_cap) + plan.arbiter_output_cap
        return CostForecast(
            input_tokens=input_ceiling,
            output_tokens=output_ceiling,
            total_tokens=input_ceiling + output_ceiling,
            cost_usd=self.cost_usd(input_ceiling, output_ceiling, model),
        )

    @staticmethod
    def _live_reservations(state: dict[str, Any]) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        live: dict[str, Any] = {}
        for key, item in state.get("active_reservations", {}).items():
            try:
                created = datetime.fromisoformat(item.get("created_at", ""))
            except ValueError:
                continue
            if created >= cutoff:
                live[key] = item
        return live

    def reserve(
        self, request: DecisionRequest, plan: GovernorPlan, model: str
    ) -> BudgetAdmission:
        forecast = self.forecast(request, plan, model)
        if forecast.total_tokens == 0:
            return BudgetAdmission(True, "", forecast, "Receipt reuse needs no reserve.")
        with self._lock:
            state = self._state()
            state["active_reservations"] = self._live_reservations(state)
            already_reserved = sum(
                int(item.get("tokens", 0))
                for item in state["active_reservations"].values()
            )
            remaining = max(
                0,
                int(state["daily_budget_tokens"])
                - int(state["daily_used_tokens"])
                - already_reserved,
            )
            if forecast.total_tokens > remaining:
                self._save(state)
                return BudgetAdmission(
                    False,
                    "",
                    forecast,
                    f"Hard Governor stopped the call: {forecast.total_tokens:,} tokens "
                    f"must be reserved but only {remaining:,} remain today.",
                )
            reservation_id = f"RES-{uuid4().hex[:12].upper()}"
            state["active_reservations"][reservation_id] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tokens": forecast.total_tokens,
                "cost_usd": forecast.cost_usd,
                "model": model,
            }
            self._save(state)
        return BudgetAdmission(True, reservation_id, forecast, "Worst-case call cost reserved.")

    def release(self, reservation_id: str) -> None:
        if not reservation_id:
            return
        with self._lock:
            state = self._state()
            state.get("active_reservations", {}).pop(reservation_id, None)
            self._save(state)

    def forfeit(self, reservation_id: str, note: str) -> None:
        """Charge an uncertain failed request at its ceiling so the cap fails closed."""
        if not reservation_id:
            return
        with self._lock:
            state = self._state()
            item = state.get("active_reservations", {}).pop(reservation_id, None)
            if not item:
                return
            tokens = int(item.get("tokens", 0))
            cost = float(item.get("cost_usd", 0))
            state["daily_used_tokens"] += tokens
            state["lifetime_used_tokens"] += tokens
            state["daily_spent_usd"] += cost
            state["lifetime_spent_usd"] += cost
            state["events"].append(
                {
                    "at": datetime.now().astimezone().isoformat(),
                    "mode": "SHED",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "saved_tokens": 0,
                    "estimated_context_tokens_avoided": 0,
                    "receipts_consulted": 0,
                    "actual_cost_usd": cost,
                    "model": item.get("model", "gpt-5.6-sol"),
                    "note": note,
                }
            )
            self._save(state)

    @staticmethod
    def fingerprint(request: DecisionRequest) -> str:
        def clean(value: str) -> str:
            return " ".join(value.lower().split())

        payload = {
            "question": clean(request.question),
            "context": clean(request.context),
            "constraints": sorted(clean(item) for item in request.constraints),
            "evidence": sorted(
                (
                    item.id,
                    clean(item.title),
                    clean(item.content),
                )
                for item in request.evidence
            ),
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(WORD.findall(text.lower()))

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        a, b = cls._terms(left), cls._terms(right)
        return len(a & b) / len(a | b) if a and b else 0.0

    @staticmethod
    def _mode(used: int, budget: int) -> str:
        ratio = used / max(1, budget)
        if ratio >= 0.9:
            return "SHED"
        if ratio >= 0.72:
            return "DWELL"
        if ratio >= 0.45:
            return "AUDIT"
        return "BUILD"

    def plan(
        self, request: DecisionRequest, records: list[dict[str, Any]]
    ) -> GovernorPlan:
        state = self._state()
        mode = self._mode(state["daily_used_tokens"], state["daily_budget_tokens"])
        fingerprint = self.fingerprint(request)
        # Curated showcase records are useful UI receipts but must never stand
        # in for a real GPT-5.6 deliberation or enter live memory context.
        decision_records = [
            r
            for r in records
            if r.get("kind") == "decision"
            and r.get("payload", {}).get("mode") == "live"
        ]
        corrections_by_decision: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            if record.get("kind") != "correction":
                continue
            decision_id = record.get("payload", {}).get("decision_id", "")
            if decision_id:
                corrections_by_decision.setdefault(decision_id, []).append(record)

        for record in reversed(decision_records):
            payload = record.get("payload", {})
            prior_request = payload.get("request", {})
            prior_fingerprint = payload.get("request_fingerprint")
            is_exact = prior_fingerprint == fingerprint or (
                prior_request and self.fingerprint(DecisionRequest.model_validate(prior_request)) == fingerprint
            )
            decision_id = payload.get("decision_id", "")
            corrections = corrections_by_decision.get(decision_id, [])
            if is_exact and not corrections:
                prior_governor = payload.get("result", {}).get("governor", {})
                actual_prior_tokens = int(prior_governor.get("input_tokens", 0)) + int(
                    prior_governor.get("output_tokens", 0)
                )
                return GovernorPlan(
                    mode=mode,
                    fingerprint=fingerprint,
                    memory_brief="",
                    receipts_consulted=1,
                    reuse_tokens_avoided=actual_prior_tokens,
                    estimated_context_tokens_avoided=0,
                    seat_output_cap=0,
                    arbiter_output_cap=0,
                    exact_record=record,
                )

        current_text = request.question + " " + request.context
        candidates: list[tuple[float, dict[str, Any], int]] = []
        raw_tokens = 0
        for record in decision_records[-60:]:
            payload = record.get("payload", {})
            prior_request = payload.get("request", {})
            prior_result = payload.get("result", {})
            score = self._similarity(current_text, prior_request.get("question", ""))
            if score >= 0.16:
                corrections = corrections_by_decision.get(payload.get("decision_id", ""), [])
                raw = json.dumps(
                    {"decision": payload, "corrections": corrections}, ensure_ascii=False
                )
                raw_tokens += self.estimate(raw)
                candidates.append((score, record, self.estimate(raw)))

        limit = {"BUILD": 3, "AUDIT": 2, "DWELL": 1, "SHED": 1}[mode]
        lines: list[str] = []
        for score, record, _ in sorted(candidates, key=lambda item: item[0], reverse=True)[:limit]:
            result = record["payload"]["result"]
            line = (
                f"Receipt {record['record_hash'][:12]} (relevance {score:.2f}): "
                f"decision={result.get('decision', '')}; "
                f"unresolved={result.get('unresolved_tension', '')}; "
                f"next_test={result.get('next_test', '')}"
            )
            corrections = corrections_by_decision.get(
                record["payload"].get("decision_id", ""), []
            )
            if corrections:
                notes = " | ".join(
                    item.get("payload", {}).get("note", "") for item in corrections[-3:]
                )
                line += f"; later_corrections={notes}"
            lines.append(line)
        brief = "\n".join(lines)[:1800]
        brief_tokens = self.estimate(brief) if brief else 0
        caps = {
            "BUILD": (1400, 2200),
            "AUDIT": (1100, 1800),
            "DWELL": (900, 1500),
            "SHED": (750, 1200),
        }
        return GovernorPlan(
            mode=mode,
            fingerprint=fingerprint,
            memory_brief=brief,
            receipts_consulted=len(lines),
            reuse_tokens_avoided=0,
            estimated_context_tokens_avoided=max(0, raw_tokens - brief_tokens),
            seat_output_cap=caps[mode][0],
            arbiter_output_cap=caps[mode][1],
        )

    def record(
        self,
        *,
        plan: GovernorPlan,
        input_tokens: int,
        output_tokens: int,
        saved_tokens: int = 0,
        estimated_context_tokens_avoided: int = 0,
        note: str,
        reservation_id: str = "",
        model: str = "gpt-5.6-sol",
    ) -> GovernorReport:
        with self._lock:
            state = self._state()
            used = max(0, input_tokens) + max(0, output_tokens)
            saved = max(0, saved_tokens)
            estimated_context = max(0, estimated_context_tokens_avoided)
            reservation = state.get("active_reservations", {}).pop(
                reservation_id, None
            )
            reserved_cost = float((reservation or {}).get("cost_usd", 0))
            actual_cost = self.cost_usd(input_tokens, output_tokens, model)
            state["daily_used_tokens"] += used
            state["daily_saved_tokens"] += saved
            state["daily_estimated_context_tokens_avoided"] += estimated_context
            state["lifetime_used_tokens"] += used
            state["lifetime_saved_tokens"] += saved
            state["daily_spent_usd"] += actual_cost
            state["lifetime_spent_usd"] += actual_cost
            state["events"].append(
                {
                    "at": datetime.now().astimezone().isoformat(),
                    "mode": plan.mode,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "saved_tokens": saved,
                    "estimated_context_tokens_avoided": estimated_context,
                    "receipts_consulted": plan.receipts_consulted,
                    "actual_cost_usd": actual_cost,
                    "model": model,
                    "note": note,
                }
            )
            self._save(state)
        return GovernorReport(
            mode=plan.mode,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            saved_tokens=saved,
            estimated_context_tokens_avoided=estimated_context,
            receipts_consulted=plan.receipts_consulted,
            actual_cost_usd=actual_cost,
            reserved_cost_usd=reserved_cost,
            note=note,
        )

    def status(self) -> dict[str, Any]:
        state = self._state()
        state["active_reservations"] = self._live_reservations(state)
        reserved_tokens = sum(
            int(item.get("tokens", 0))
            for item in state["active_reservations"].values()
        )
        reserved_usd = sum(
            float(item.get("cost_usd", 0))
            for item in state["active_reservations"].values()
        )
        state["mode"] = self._mode(
            state["daily_used_tokens"], state["daily_budget_tokens"]
        )
        state["reserved_tokens"] = reserved_tokens
        state["reserved_usd"] = round(reserved_usd, 6)
        state["remaining_tokens"] = max(
            0,
            state["daily_budget_tokens"]
            - state["daily_used_tokens"]
            - reserved_tokens,
        )
        return state
