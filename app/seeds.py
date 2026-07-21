from __future__ import annotations

import hashlib
import json
import re
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import DecisionRequest, EvidenceItem, SeedCreate, SeedEvidenceCreate
from .ledger import AppendOnlyLedger


WORD = re.compile(r"[a-z0-9]{3,}")
CONTRADICTION_CUES = {
    "blocked",
    "breach",
    "contradicted",
    "corrected",
    "crash",
    "decreased",
    "dropped",
    "exceeded",
    "failed",
    "increased",
    "missed",
    "regression",
    "revoked",
    "unavailable",
    "worse",
    "worsened",
}


@dataclass
class WakeAssessment:
    should_wake: bool
    score: float
    threshold: float
    reason: str
    new_evidence: int

    def model_dump(self) -> dict[str, Any]:
        return {
            "should_wake": self.should_wake,
            "score": self.score,
            "threshold": self.threshold,
            "reason": self.reason,
            "new_evidence": self.new_evidence,
        }


@dataclass
class SeedBudgetAdmission:
    allowed: bool
    reservation_id: str
    reserved_usd: float
    reason: str


class SeedRegistry:
    """Event-sourced planted decisions with deterministic wake and spend gates."""

    def __init__(self, path: Path) -> None:
        self.ledger = AppendOnlyLedger(path)
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _words(text: str) -> set[str]:
        return set(WORD.findall(text.lower()))

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        a, b = cls._words(left), cls._words(right)
        return len(a & b) / len(a | b) if a and b else 0.0

    @staticmethod
    def _evidence_hash(title: str, content: str) -> str:
        normalized = " ".join(f"{title} {content}".lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _states(self) -> dict[str, dict[str, Any]]:
        states: dict[str, dict[str, Any]] = {}
        for record in self.ledger.records():
            payload = record.get("payload", {})
            seed_id = payload.get("seed_id", "")
            kind = record.get("kind")
            if kind == "seed_planted":
                states[seed_id] = {
                    "seed_id": seed_id,
                    "created_at": record["timestamp"],
                    "updated_at": record["timestamp"],
                    "expires_at": payload["expires_at"],
                    "status": "dormant",
                    "question": payload["question"],
                    "context": payload.get("context", ""),
                    "constraints": payload.get("constraints", []),
                    "evidence": list(payload.get("evidence", [])),
                    "budget_usd": float(payload["budget_usd"]),
                    "spent_usd": 0.0,
                    "reserved": {},
                    "auto_bloom": bool(payload.get("auto_bloom", False)),
                    "check_interval_hours": int(
                        payload.get("check_interval_hours", 24)
                    ),
                    "next_check_at": record["timestamp"],
                    "checks": 0,
                    "wakes": 0,
                    "sleeps": 0,
                    "consecutive_sleeps": 0,
                    "last_bloom_version": 0,
                    "last_assessment": None,
                    "latest_decision_id": "",
                    "latest_receipt_hash": "",
                    "event_count": 1,
                }
                continue
            state = states.get(seed_id)
            if not state:
                continue
            state["updated_at"] = record["timestamp"]
            state["event_count"] += 1
            if kind == "seed_evidence_added":
                state["evidence"].append(payload["evidence"])
                state["next_check_at"] = record["timestamp"]
            elif kind == "seed_checked":
                state["checks"] += 1
                state["last_assessment"] = payload["assessment"]
                state["next_check_at"] = payload["next_check_at"]
                if payload["assessment"]["should_wake"]:
                    state["wakes"] += 1
                    state["status"] = "sprouting"
                else:
                    state["sleeps"] += 1
                    state["consecutive_sleeps"] += 1
                    state["status"] = "dormant"
            elif kind == "seed_budget_reserved":
                state["reserved"][payload["reservation_id"]] = float(
                    payload["reserved_usd"]
                )
                state["status"] = "growing"
            elif kind == "seed_budget_released":
                state["reserved"].pop(payload["reservation_id"], None)
            elif kind == "seed_budget_settled":
                state["reserved"].pop(payload["reservation_id"], None)
                state["spent_usd"] += float(payload["actual_cost_usd"])
            elif kind == "seed_bloomed":
                state["latest_decision_id"] = payload["decision_id"]
                state["latest_receipt_hash"] = payload["receipt_hash"]
                state["last_bloom_version"] = int(payload["evidence_version"])
                state["consecutive_sleeps"] = 0
                state["status"] = "dormant"
                state["next_check_at"] = payload["next_check_at"]
            elif kind == "seed_harvested":
                state["status"] = "harvested"

        for state in states.values():
            reserved_usd = sum(state.pop("reserved", {}).values())
            state["reserved_usd"] = round(reserved_usd, 6)
            state["spent_usd"] = round(state["spent_usd"], 6)
            state["remaining_usd"] = round(
                max(0.0, state["budget_usd"] - state["spent_usd"] - reserved_usd),
                6,
            )
            state["evidence_version"] = len(state["evidence"])
            state["expired"] = self._now() >= datetime.fromisoformat(
                state["expires_at"]
            )
            if state["status"] != "harvested" and (
                state["expired"] or state["remaining_usd"] <= 0
            ):
                state["status"] = "shed"
        return states

    def list(self) -> list[dict[str, Any]]:
        return sorted(
            self._states().values(), key=lambda item: item["created_at"], reverse=True
        )

    def get(self, seed_id: str) -> dict[str, Any] | None:
        return self._states().get(seed_id)

    def plant(self, request: SeedCreate) -> dict[str, Any]:
        seed_id = f"SEED-{uuid4().hex[:8].upper()}"
        expires_at = self._now() + timedelta(days=request.duration_days)
        self.ledger.append(
            "seed_planted",
            {
                "seed_id": seed_id,
                "question": request.question,
                "context": request.context,
                "constraints": request.constraints,
                "evidence": [item.model_dump() for item in request.evidence],
                "budget_usd": request.budget_usd,
                "duration_days": request.duration_days,
                "check_interval_hours": request.check_interval_hours,
                "auto_bloom": request.auto_bloom,
                "expires_at": expires_at.isoformat(),
            },
        )
        return self.get(seed_id) or {}

    def add_evidence(
        self, seed_id: str, update: SeedEvidenceCreate
    ) -> tuple[dict[str, Any] | None, bool]:
        with self._lock:
            state = self.get(seed_id)
            if not state or state["status"] in {"harvested", "shed"}:
                return state, False
            new_hash = self._evidence_hash(update.title, update.content)
            existing_hashes = {
                self._evidence_hash(item["title"], item["content"])
                for item in state["evidence"]
            }
            if new_hash in existing_hashes:
                self.ledger.append(
                    "seed_evidence_rejected",
                    {"seed_id": seed_id, "reason": "exact duplicate", "hash": new_hash},
                )
                return self.get(seed_id), False
            if len(state["evidence"]) >= 99:
                return state, False
            evidence = {
                "id": f"E{len(state['evidence']) + 1}",
                "title": update.title.strip(),
                "content": update.content.strip(),
            }
            self.ledger.append(
                "seed_evidence_added", {"seed_id": seed_id, "evidence": evidence}
            )
            return self.get(seed_id), True

    def assess(self, seed_id: str) -> WakeAssessment:
        state = self.get(seed_id)
        if not state:
            raise KeyError(seed_id)
        threshold = min(0.78, 0.38 + 0.05 * state["consecutive_sleeps"])
        if state["status"] in {"harvested", "shed"}:
            return WakeAssessment(False, 0.0, threshold, "Seed is no longer active.", 0)
        if not state["latest_decision_id"]:
            return WakeAssessment(
                True,
                1.0,
                threshold,
                "Initial baseline has not been deliberated.",
                len(state["evidence"]),
            )
        new_items = state["evidence"][state["last_bloom_version"] :]
        if not new_items:
            return WakeAssessment(
                False, 0.0, threshold, "No evidence changed since the last bloom.", 0
            )
        old_items = state["evidence"][: state["last_bloom_version"]]
        focus = " ".join(
            [state["question"], state["context"], *state["constraints"]]
        )
        focus_words = self._words(focus)
        novelty_scores: list[float] = []
        relevance_scores: list[float] = []
        contradiction_scores: list[float] = []
        for item in new_items:
            text = f"{item['title']} {item['content']}"
            prior_similarity = max(
                (
                    self._similarity(
                        text, f"{prior['title']} {prior['content']}"
                    )
                    for prior in old_items
                ),
                default=0.0,
            )
            item_words = self._words(text)
            relevance = (
                len(item_words & focus_words) / min(len(item_words), len(focus_words))
                if item_words and focus_words
                else 0.0
            )
            novelty_scores.append(1.0 - prior_similarity)
            relevance_scores.append(relevance)
            contradiction_scores.append(
                1.0 if item_words & CONTRADICTION_CUES else 0.0
            )
        novelty = max(novelty_scores)
        relevance = max(relevance_scores)
        contradiction = max(contradiction_scores)
        score = round(
            min(1.0, 0.35 * novelty + 0.40 * relevance + 0.25 * contradiction),
            3,
        )
        # Backoff quiets routine novelty, but a relevant contradiction must be
        # able to wake an old seed immediately.
        if contradiction and relevance >= 0.20:
            threshold = min(threshold, 0.42)
        should_wake = score >= threshold
        reason = (
            f"Material delta crossed the wake gate: novelty {novelty:.2f}, "
            f"relevance {relevance:.2f}, contradiction {contradiction:.2f}."
            if should_wake
            else f"Delta stayed below the wake gate: novelty {novelty:.2f}, "
            f"relevance {relevance:.2f}, contradiction {contradiction:.2f}."
        )
        return WakeAssessment(should_wake, score, threshold, reason, len(new_items))

    def check(self, seed_id: str) -> WakeAssessment:
        with self._lock:
            state = self.get(seed_id)
            if not state:
                raise KeyError(seed_id)
            assessment = self.assess(seed_id)
            backoff = 1 if assessment.should_wake else 2 ** min(
                state["consecutive_sleeps"] + 1, 4
            )
            next_check = self._now() + timedelta(
                hours=state["check_interval_hours"] * backoff
            )
            self.ledger.append(
                "seed_checked",
                {
                    "seed_id": seed_id,
                    "assessment": assessment.model_dump(),
                    "next_check_at": next_check.isoformat(),
                },
            )
            return assessment

    def reserve(self, seed_id: str, cost_usd: float) -> SeedBudgetAdmission:
        if cost_usd <= 0:
            return SeedBudgetAdmission(True, "", 0.0, "No model spend required.")
        with self._lock:
            state = self.get(seed_id)
            if not state:
                return SeedBudgetAdmission(False, "", 0.0, "Seed not found.")
            if state["status"] in {"harvested", "shed"}:
                return SeedBudgetAdmission(False, "", 0.0, "Seed is no longer active.")
            if cost_usd > state["remaining_usd"]:
                return SeedBudgetAdmission(
                    False,
                    "",
                    0.0,
                    f"Seed budget stopped the bloom: ${cost_usd:.4f} must be "
                    f"reserved but ${state['remaining_usd']:.4f} remains.",
                )
            reservation_id = f"SRES-{uuid4().hex[:12].upper()}"
            self.ledger.append(
                "seed_budget_reserved",
                {
                    "seed_id": seed_id,
                    "reservation_id": reservation_id,
                    "reserved_usd": round(cost_usd, 6),
                },
            )
            return SeedBudgetAdmission(
                True, reservation_id, round(cost_usd, 6), "Seed budget reserved."
            )

    def release(self, seed_id: str, reservation_id: str, reason: str) -> None:
        if reservation_id:
            self.ledger.append(
                "seed_budget_released",
                {
                    "seed_id": seed_id,
                    "reservation_id": reservation_id,
                    "reason": reason,
                },
            )

    def settle(
        self,
        seed_id: str,
        reservation_id: str,
        actual_cost_usd: float,
        outcome: str = "completed",
    ) -> None:
        if not reservation_id and actual_cost_usd <= 0:
            return
        self.ledger.append(
            "seed_budget_settled",
            {
                "seed_id": seed_id,
                "reservation_id": reservation_id,
                "actual_cost_usd": round(max(0.0, actual_cost_usd), 6),
                "outcome": outcome,
            },
        )

    def bloom(self, seed_id: str, decision_id: str, receipt_hash: str) -> dict[str, Any]:
        state = self.get(seed_id)
        if not state:
            raise KeyError(seed_id)
        next_check = self._now() + timedelta(hours=state["check_interval_hours"])
        self.ledger.append(
            "seed_bloomed",
            {
                "seed_id": seed_id,
                "decision_id": decision_id,
                "receipt_hash": receipt_hash,
                "evidence_version": len(state["evidence"]),
                "next_check_at": next_check.isoformat(),
            },
        )
        return self.get(seed_id) or {}

    def harvest(self, seed_id: str, reason: str = "Harvested by owner.") -> dict[str, Any] | None:
        if not self.get(seed_id):
            return None
        self.ledger.append("seed_harvested", {"seed_id": seed_id, "reason": reason})
        return self.get(seed_id)

    def due(self) -> list[dict[str, Any]]:
        now = self._now()
        return [
            seed
            for seed in self.list()
            if seed["auto_bloom"]
            and seed["status"] not in {"harvested", "shed"}
            and datetime.fromisoformat(seed["next_check_at"]) <= now
        ]

    def decision_request(self, seed_id: str) -> DecisionRequest:
        state = self.get(seed_id)
        if not state:
            raise KeyError(seed_id)
        evidence = state["evidence"][-10:]
        return DecisionRequest(
            question=state["question"],
            context=state["context"],
            constraints=state["constraints"],
            evidence=[EvidenceItem.model_validate(item) for item in evidence],
        )

    def verify(self) -> dict[str, Any]:
        return self.ledger.verify()


def simulate_growth(
    *, days: int = 30, budget_usd: float = 1.0, material_every_days: int = 7
) -> dict[str, Any]:
    """Run a deterministic, zero-API longitudinal test of wake and budget logic."""
    with tempfile.TemporaryDirectory(prefix="dissent-seed-sim-") as folder:
        registry = SeedRegistry(Path(folder) / "seed_ledger.jsonl")
        seed = registry.plant(
            SeedCreate(
                question="Should the product team continue the staged rollout based on reliability evidence?",
                context="The rollout should advance only when product reliability remains acceptable.",
                constraints=["Stop if reliability worsens"],
                evidence=[
                    EvidenceItem(
                        id="E1",
                        title="Initial reliability",
                        content="The staged rollout began with stable product reliability.",
                    )
                ],
                budget_usd=budget_usd,
                duration_days=days,
            )
        )
        seed_id = seed["seed_id"]
        wakes = sleeps = false_wakes = simulated_blooms = rejected_duplicates = 0
        reserve_ceiling = 0.22
        simulated_actual = 0.109

        initial = registry.check(seed_id)
        if initial.should_wake:
            wakes += 1
            admission = registry.reserve(seed_id, reserve_ceiling)
            if admission.allowed:
                registry.settle(seed_id, admission.reservation_id, simulated_actual)
                registry.bloom(seed_id, "SIM-BASELINE", "0" * 64)
                simulated_blooms += 1

        for day in range(1, days + 1):
            is_material = day % material_every_days == 0
            update = (
                SeedEvidenceCreate(
                    title=f"Reliability regression day {day}",
                    content=(
                        "Product reliability worsened and the staged rollout failed "
                        "the reliability constraint."
                    ),
                )
                if is_material
                else SeedEvidenceCreate(
                    title=f"Routine heartbeat day {day}",
                    content="Routine calendar heartbeat with no decision-relevant change.",
                )
            )
            _, added = registry.add_evidence(seed_id, update)
            if not added:
                rejected_duplicates += 1
                continue
            assessment = registry.check(seed_id)
            if assessment.should_wake:
                wakes += 1
                if not is_material:
                    false_wakes += 1
                admission = registry.reserve(seed_id, reserve_ceiling)
                if admission.allowed:
                    registry.settle(
                        seed_id, admission.reservation_id, simulated_actual
                    )
                    registry.bloom(
                        seed_id, f"SIM-{day:03d}", f"{day:064x}"[-64:]
                    )
                    simulated_blooms += 1
            else:
                sleeps += 1

        final = registry.get(seed_id) or {}
        noise_checks = max(1, days - (days // material_every_days))
        return {
            "days": days,
            "checks": wakes + sleeps,
            "wakes": wakes,
            "sleeps": sleeps,
            "false_wakes": false_wakes,
            "false_wake_rate": round(false_wakes / noise_checks, 3),
            "simulated_blooms": simulated_blooms,
            "rejected_duplicates": rejected_duplicates,
            "budget_usd": budget_usd,
            "spent_usd": final.get("spent_usd", 0.0),
            "remaining_usd": final.get("remaining_usd", 0.0),
            "budget_breaches": int(final.get("spent_usd", 0.0) > budget_usd),
            "ledger_valid": registry.verify()["valid"],
        }
