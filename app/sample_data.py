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
    question=(
        "Should our six-person product team release the new onboarding flow to "
        "100% of users on Friday, or begin with a 10% staged rollout?"
    ),
    context=(
        "The redesign improved activation in beta, but the team saw an Android "
        "reliability regression. A coordinated marketing campaign begins Monday."
    ),
    constraints=[
        "Protect Android reliability",
        "Any rollout must be reversible within 30 minutes",
        "Customer support has no weekend coverage",
        "The marketing campaign begins Monday morning",
    ],
    evidence=[
        EvidenceItem(
            id="E1",
            title="Beta activation",
            content=(
                "The redesigned flow increased completed activation by 8.2% relative "
                "to control among 212 beta participants."
            ),
        ),
        EvidenceItem(
            id="E2",
            title="Android reliability",
            content=(
                "Android crash-free sessions fell from 99.4% to 97.8% during the beta. "
                "The cause has not been isolated."
            ),
        ),
        EvidenceItem(
            id="E3",
            title="Support schedule",
            content="Customer support has no scheduled coverage from Friday 6 PM until Monday 8 AM.",
        ),
        EvidenceItem(
            id="E4",
            title="Rollback drills",
            content="Three rollback drills completed in 14, 18, and 22 minutes.",
        ),
        EvidenceItem(
            id="E5",
            title="Campaign flexibility",
            content="Marketing can point Monday's campaign to a waitlist without penalty until Sunday noon.",
        ),
    ],
)


def showcase_result() -> DeliberationResult:
    seats = [
        SeatPass(
            seat="builder",
            thesis=(
                "Capture the activation gain through a staged rollout with explicit "
                "reliability gates instead of exposing every user at once."
            ),
            claims=[
                SeatClaim(
                    statement="The beta provides a credible signal that the redesign can improve activation.",
                    evidence_ids=["E1"],
                    confidence=0.82,
                ),
                SeatClaim(
                    statement="The team has demonstrated rollback within the required 30-minute window.",
                    evidence_ids=["E4"],
                    confidence=0.96,
                ),
            ],
            question_for_others="What Android stop threshold would make a staged rollout acceptably reversible?",
        ),
        SeatPass(
            seat="breaker",
            thesis=(
                "A Friday release externalizes an unresolved Android defect into a period "
                "with no support coverage, so even a small stage needs timing controls."
            ),
            claims=[
                SeatClaim(
                    statement="The Android reliability regression is material and unexplained.",
                    evidence_ids=["E2"],
                    confidence=0.97,
                ),
                SeatClaim(
                    statement="A Friday rollout could leave affected users without support until Monday.",
                    evidence_ids=["E3"],
                    confidence=0.93,
                ),
            ],
            question_for_others="Why accept weekend exposure when the campaign can still be redirected?",
        ),
        SeatPass(
            seat="grounder",
            thesis=(
                "The evidence supports testing activation upside and avoiding a full launch; "
                "it does not establish that the Android regression is safe at any scale."
            ),
            claims=[
                SeatClaim(
                    statement="The activation estimate comes from a modest beta sample and remains uncertain.",
                    evidence_ids=["E1"],
                    confidence=0.86,
                ),
                SeatClaim(
                    statement="Campaign timing does not force a Friday production release.",
                    evidence_ids=["E5"],
                    confidence=0.95,
                ),
            ],
            question_for_others="What observation during the stage would justify expanding beyond 10%?",
        ),
    ]
    claims = [
        AdjudicatedClaim(
            id="C1",
            statement="The redesign produced an activation improvement in beta.",
            status=ClaimStatus.SURVIVED,
            evidence_ids=["E1"],
            supporting_seats=["builder", "grounder"],
            challenge="The 212-person sample does not establish the production effect size.",
        ),
        AdjudicatedClaim(
            id="C2",
            statement="The Android build has a material unresolved reliability regression.",
            status=ClaimStatus.SURVIVED,
            evidence_ids=["E2"],
            supporting_seats=["breaker", "grounder"],
            challenge="The evidence identifies the regression but not its cause or affected segments.",
        ),
        AdjudicatedClaim(
            id="C3",
            statement="The release can be reversed inside the required 30-minute window.",
            status=ClaimStatus.SURVIVED,
            evidence_ids=["E4"],
            supporting_seats=["builder"],
            challenge="Drills may be faster than rollback under live incident pressure.",
        ),
        AdjudicatedClaim(
            id="C4",
            statement="A 10% Friday rollout is safe without active support coverage.",
            status=ClaimStatus.DISPUTED,
            evidence_ids=["E2", "E3"],
            supporting_seats=["breaker"],
            challenge="The evidence shows exposure and absent support, not an acceptable risk threshold.",
        ),
        AdjudicatedClaim(
            id="C5",
            statement="A 100% release will preserve the beta activation lift.",
            status=ClaimStatus.UNSUPPORTED,
            evidence_ids=["E1"],
            supporting_seats=["builder"],
            challenge="Beta direction is supported; production-scale effect size is not.",
        ),
    ]
    return DeliberationResult(
        mode="showcase",
        model="curated GPT-5.6-shaped showcase",
        question=SAMPLE_REQUEST.question,
        seats=seats,
        claims=claims,
        surviving_core=(
            "The activation upside deserves a controlled production test, while the unexplained "
            "Android regression and weekend support gap rule out a full Friday release."
        ),
        unresolved_tension=(
            "A staged rollout creates useful production evidence, but beginning it without support "
            "coverage exposes users before the team can respond normally."
        ),
        next_test=(
            "Begin a 10% rollout Monday at 9 AM with an Android crash-free stop threshold of 99.0%, "
            "a named rollback owner, and a review after 500 activated users."
        ),
        decision="Stage the rollout at 10% on Monday; do not release to 100% on Friday.",
        claim_survival_rate=0.6,
    )

