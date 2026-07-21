from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ClaimStatus(str, Enum):
    SURVIVED = "survived"
    DISPUTED = "disputed"
    UNSUPPORTED = "unsupported"


class EvidenceItem(BaseModel):
    id: str = Field(pattern=r"^E\d{1,2}$")
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=3, max_length=1800)


class DecisionRequest(BaseModel):
    question: str = Field(min_length=10, max_length=800)
    context: str = Field(default="", max_length=3000)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=10)

    @field_validator("constraints")
    @classmethod
    def clean_constraints(cls, values: list[str]) -> list[str]:
        return [value.strip()[:300] for value in values if value.strip()]

    @model_validator(mode="after")
    def unique_evidence_ids(self) -> "DecisionRequest":
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique")
        return self


class SeatClaim(BaseModel):
    statement: str = Field(min_length=5, max_length=420)
    evidence_ids: list[str] = Field(default_factory=list, max_length=6)
    confidence: float = Field(ge=0, le=1)


class SeatPass(BaseModel):
    seat: Literal["builder", "breaker", "grounder"]
    thesis: str = Field(min_length=10, max_length=700)
    claims: list[SeatClaim] = Field(min_length=2, max_length=6)
    question_for_others: str = Field(min_length=5, max_length=300)


class AdjudicatedClaim(BaseModel):
    id: str = Field(pattern=r"^C\d{1,2}$")
    statement: str = Field(min_length=5, max_length=420)
    status: ClaimStatus
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    supporting_seats: list[Literal["builder", "breaker", "grounder"]] = Field(
        default_factory=list
    )
    challenge: str = Field(default="", max_length=420)


class GovernorReport(BaseModel):
    mode: Literal["BUILD", "AUDIT", "DWELL", "SHED"] = "BUILD"
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    saved_tokens: int = Field(default=0, ge=0)
    estimated_context_tokens_avoided: int = Field(default=0, ge=0)
    receipts_consulted: int = Field(default=0, ge=0)
    receipt_reused: str = ""
    actual_cost_usd: float = Field(default=0, ge=0)
    reserved_cost_usd: float = Field(default=0, ge=0)
    note: str = "No prior receipt was relevant."


class DeliberationResult(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"DG-{uuid4().hex[:8].upper()}")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    mode: Literal["live", "showcase", "reused"]
    model: str
    question: str
    seats: list[SeatPass]
    claims: list[AdjudicatedClaim]
    surviving_core: str = Field(min_length=10, max_length=900)
    unresolved_tension: str = Field(min_length=5, max_length=700)
    next_test: str = Field(min_length=5, max_length=700)
    decision: str = Field(min_length=5, max_length=700)
    claim_survival_rate: float = Field(ge=0, le=1)
    governor: GovernorReport = Field(default_factory=GovernorReport)
    receipt_hash: str = ""


class CorrectionRequest(BaseModel):
    note: str = Field(min_length=5, max_length=1200)


class SeedCreate(DecisionRequest):
    budget_usd: float = Field(default=1.0, ge=0.10, le=100)
    duration_days: int = Field(default=30, ge=1, le=365)
    check_interval_hours: int = Field(default=24, ge=1, le=168)
    auto_bloom: bool = False


class SeedEvidenceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=3, max_length=1800)


class SeedCheckRequest(BaseModel):
    run_model: bool = False


class SeedSimulationRequest(BaseModel):
    days: int = Field(default=30, ge=7, le=365)
    budget_usd: float = Field(default=1.0, ge=0.10, le=100)
    material_every_days: int = Field(default=7, ge=2, le=60)
