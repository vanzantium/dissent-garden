# Build Week Development Log

All times are Pacific Time. Git history is the authoritative implementation
record; this file provides the human-readable narrative required for judging.

## July 17, 2026

- **21:27** — Created the new `dissent_garden` repository during the submission
  period.
- Defined the product boundary: evidence-bound team decisions, role-separated
  seats, preserved dissent, reversible next tests.
- Verified the current GPT-5.6 model alias and Responses API structured-output
  support against official OpenAI developer documentation.
- Implemented Builder, Breaker, and Grounder as concurrent, isolated GPT-5.6
  role passes.
- Implemented the GPT-5.6 arbiter and server-side evidence citation validation.
- Implemented a hash-chained append-only decision and correction ledger.
- Built the responsive decision-board interface and curated showcase path.
- Ran the application in the local in-app browser and verified the sample,
  result, correction, decision history, desktop, and mobile flows.
- Added the receipt-aware Token Governor: exact live-receipt reuse, relevant
  memory ranking, bounded compaction, adaptive output caps, and token accounting.
- Added automated coverage for ledger tampering, cache provenance, compaction,
  budget accounting, and API boundaries.
- Ran a product-level dissent audit and tightened the result: correction-aware
  reuse, canonical fingerprints, validated correction targets, bounded API
  retries/timeouts, untrusted-evidence prompt boundaries, and honest separation
  of actual token savings from estimated context reduction.
- Replaced the generic meeting showcase with a staged product-rollout decision
  and added a preregistered blind comparison plan with fixed evaluation assets.
- **July 21** — Completed the first real GPT-5.6 Sol four-call deliberation:
  3,769 input tokens, 2,997 output tokens, 46.83 seconds, and a valid live receipt.
  Repeated the exact request in 84 ms with zero model calls and 6,766 actual prior
  tokens avoided. See `docs/LIVE_TEST_2026-07-21.md` for the transparent record.
- **July 21** — Added Plant a Seed: an append-only seed registry, deterministic
  wake/backoff gate, duplicate suppression, opt-in local autopilot, hard token
  and USD reservations, manual evidence updates, harvesting, and a zero-API
  longitudinal simulator. The initial 30-day fixture produced 26 sleeps, five
  material wakes, no false wakes, no budget breach, and a valid seed ledger.

## Evidence to retain for submission

- This repository's dated Git history.
- The primary Codex task and its `/feedback` session ID.
- Screenshots or a short recording of Codex building and testing the project.
- The public demo video showing live GPT-5.6 output and the Governor panel.
