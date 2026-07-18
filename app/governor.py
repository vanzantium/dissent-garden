from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import DecisionRequest, GovernorReport


WORD = re.compile(r"[a-z0-9]{3,}")


@dataclass
class GovernorPlan:
    mode: str
    fingerprint: str
    memory_brief: str
    receipts_consulted: int
    estimated_saved: int
    seat_output_cap: int
    arbiter_output_cap: int
    exact_record: dict[str, Any] | None = None


class TokenGovernor:
    """Receipt-aware context and token governor.

    It never rewrites history. Exact repeats reuse a verified prior result;
    near-relevant receipts are ranked and compressed into a bounded brief.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.daily_budget = int(os.getenv("DISSENT_GARDEN_DAILY_TOKEN_BUDGET", "100000"))

    @staticmethod
    def _today() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d")

    def _state(self) -> dict[str, Any]:
        default = {
            "day": self._today(),
            "daily_budget_tokens": self.daily_budget,
            "daily_used_tokens": 0,
            "daily_saved_tokens": 0,
            "lifetime_used_tokens": 0,
            "lifetime_saved_tokens": 0,
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
                day=self._today(), daily_used_tokens=0, daily_saved_tokens=0, events=[]
            )
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
    def fingerprint(request: DecisionRequest) -> str:
        payload = request.model_dump()
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()
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

        for record in reversed(decision_records):
            payload = record.get("payload", {})
            prior_request = payload.get("request", {})
            prior_fingerprint = payload.get("request_fingerprint")
            if prior_fingerprint == fingerprint or (
                prior_request and self.fingerprint(DecisionRequest.model_validate(prior_request)) == fingerprint
            ):
                return GovernorPlan(
                    mode=mode,
                    fingerprint=fingerprint,
                    memory_brief="",
                    receipts_consulted=1,
                    estimated_saved=self.estimate(json.dumps(prior_request)) * 4 + 3200,
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
                raw = json.dumps(payload, ensure_ascii=False)
                raw_tokens += self.estimate(raw)
                candidates.append((score, record, self.estimate(raw)))

        limit = {"BUILD": 3, "AUDIT": 2, "DWELL": 1, "SHED": 1}[mode]
        lines: list[str] = []
        for score, record, _ in sorted(candidates, key=lambda item: item[0], reverse=True)[:limit]:
            result = record["payload"]["result"]
            lines.append(
                f"Receipt {record['record_hash'][:12]} (relevance {score:.2f}): "
                f"decision={result.get('decision', '')}; "
                f"unresolved={result.get('unresolved_tension', '')}; "
                f"next_test={result.get('next_test', '')}"
            )
        brief = "\n".join(lines)[:1800]
        brief_tokens = self.estimate(brief) if brief else 0
        caps = {
            "BUILD": (1200, 1800),
            "AUDIT": (900, 1400),
            "DWELL": (700, 1100),
            "SHED": (550, 900),
        }
        return GovernorPlan(
            mode=mode,
            fingerprint=fingerprint,
            memory_brief=brief,
            receipts_consulted=len(lines),
            estimated_saved=max(0, raw_tokens - brief_tokens),
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
        note: str,
    ) -> GovernorReport:
        with self._lock:
            state = self._state()
            used = max(0, input_tokens) + max(0, output_tokens)
            saved = max(0, saved_tokens)
            state["daily_used_tokens"] += used
            state["daily_saved_tokens"] += saved
            state["lifetime_used_tokens"] += used
            state["lifetime_saved_tokens"] += saved
            state["events"].append(
                {
                    "at": datetime.now().astimezone().isoformat(),
                    "mode": plan.mode,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "saved_tokens": saved,
                    "receipts_consulted": plan.receipts_consulted,
                    "note": note,
                }
            )
            self._save(state)
        return GovernorReport(
            mode=plan.mode,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            saved_tokens=saved,
            receipts_consulted=plan.receipts_consulted,
            note=note,
        )

    def status(self) -> dict[str, Any]:
        state = self._state()
        state["mode"] = self._mode(
            state["daily_used_tokens"], state["daily_budget_tokens"]
        )
        state["remaining_tokens"] = max(
            0, state["daily_budget_tokens"] - state["daily_used_tokens"]
        )
        return state
