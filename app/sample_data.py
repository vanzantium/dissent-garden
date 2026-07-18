from __future__ import annotations

from .contracts import (
    AdjudicatedClaim,
    ClaimStatus,
    DecisionRequest,
    DeliberationResult,
    EvidenceItem,
    SeatClaim,
    SeatPass,
)


SAMPLE_REQUEST = DecisionRequest(
    question="Should our four-person product team replace weekly status meetings with an asynchronous written update for a six-week trial?",
    context=(
        "The team wants more focus time without losing early warning signals. "
        "Two people work remotely and two share an office."
    ),
    constraints=[
        "No new paid software",
        "The trial must be reversible",
        "Blocked work must become visible within one business day",
    ],
    evidence=[
        EvidenceItem(
            id="E1",
            title="Meeting sample",
            content="The last six status meetings averaged 47 minutes for four people.",
        ),
        EvidenceItem(
            id="E2",
            title="Team pulse",
            content="Three of four teammates asked for more uninterrupted mornings.",
        ),
        EvidenceItem(
            id="E3",
            title="Recent incident",
            content="A dependency risk surfaced three days late when its owner missed a meeting.",
        ),
    ],
)


def showcase_result() -> DeliberationResult:
    seats = [
        SeatPass(
            seat="builder",
            thesis="Run a bounded asynchronous trial because the time cost is measurable and the change is reversible.",
            claims=[
                SeatClaim(
                    statement="The current meeting consumes more than three team-hours each week.",
                    evidence_ids=["E1"],
                    confidence=0.98,
                ),
                SeatClaim(
                    statement="A written update can return focus time to most of the team.",
                    evidence_ids=["E2"],
                    confidence=0.78,
                ),
            ],
            question_for_others="What minimum escalation rule would prevent silence from hiding a blocker?",
        ),
        SeatPass(
            seat="breaker",
            thesis="The meeting is not the real risk; an asynchronous process can make weak signals easier to ignore.",
            claims=[
                SeatClaim(
                    statement="A missed synchronous checkpoint has already delayed a dependency warning.",
                    evidence_ids=["E3"],
                    confidence=0.93,
                ),
                SeatClaim(
                    statement="Written updates may reduce spontaneous cross-team problem solving.",
                    evidence_ids=[],
                    confidence=0.44,
                ),
            ],
            question_for_others="Who is accountable when an update contains a blocker but nobody responds?",
        ),
        SeatPass(
            seat="grounder",
            thesis="The evidence supports testing a change, but not permanently removing synchronous contact.",
            claims=[
                SeatClaim(
                    statement="The time burden and demand for focus are supported by the supplied evidence.",
                    evidence_ids=["E1", "E2"],
                    confidence=0.96,
                ),
                SeatClaim(
                    statement="The evidence does not show that asynchronous updates catch blockers reliably.",
                    evidence_ids=["E3"],
                    confidence=0.9,
                ),
            ],
            question_for_others="What observable threshold would cause the team to restore the meeting?",
        ),
    ]
    claims = [
        AdjudicatedClaim(
            id="C1",
            statement="The existing meeting costs more than three team-hours per week.",
            status=ClaimStatus.SURVIVED,
            evidence_ids=["E1"],
            supporting_seats=["builder", "grounder"],
            challenge="The sample is only six weeks, but the arithmetic is direct.",
        ),
        AdjudicatedClaim(
            id="C2",
            statement="Most of the team wants more uninterrupted morning work.",
            status=ClaimStatus.SURVIVED,
            evidence_ids=["E2"],
            supporting_seats=["builder", "grounder"],
            challenge="Preference does not prove that removing meetings improves delivery.",
        ),
        AdjudicatedClaim(
            id="C3",
            statement="Asynchronous updates will surface blockers within one day.",
            status=ClaimStatus.DISPUTED,
            evidence_ids=["E3"],
            supporting_seats=["breaker", "grounder"],
            challenge="The only supplied incident shows a warning arriving late; the proposed process is untested.",
        ),
        AdjudicatedClaim(
            id="C4",
            statement="Written updates will improve spontaneous collaboration.",
            status=ClaimStatus.UNSUPPORTED,
            evidence_ids=[],
            supporting_seats=["breaker"],
            challenge="No supplied evidence measures collaboration quality.",
        ),
    ]
    return DeliberationResult(
        mode="showcase",
        model="curated GPT-5.6-shaped showcase",
        question=SAMPLE_REQUEST.question,
        seats=seats,
        claims=claims,
        surviving_core=(
            "A reversible trial is justified by the measurable meeting cost and the team’s stated need for focus time. "
            "The trial should not assume that writing alone makes blockers visible."
        ),
        unresolved_tension=(
            "Focus time improves only if the team can replace ambient awareness with an explicit, owned escalation path."
        ),
        next_test=(
            "Run the asynchronous update for two weeks. Require blockers to name an owner and deadline, and restore a 15-minute sync if any blocker waits more than one business day for acknowledgement."
        ),
        decision="Proceed with a two-week reversible trial with a blocker acknowledgement rule.",
        evidence_coverage=0.75,
    )

