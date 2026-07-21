# Dissent Garden — Under-Three-Minute Demo

Target finished length: **2:40–2:50**. Record at 1080p with English voiceover.
The video must be public on YouTube. Do not show an API key, billing page,
private corpus, third-party logo, personal decision, or copyrighted music.

## Recording setup

1. Use a fresh data directory for an uncluttered ledger:
   `$env:DISSENT_GARDEN_DATA_DIR="$PWD\data\recording"` on Windows.
2. Start the app with the API key already in the process environment.
3. Load the staged rollout example before recording.
4. Record the live run once, then record the exact receipt-reuse run.
5. Edit the 40–60 second model wait down to a 3–5 second montage containing a
   Codex test/build clip. Do not imply that the unedited model latency was five
   seconds.
6. Keep browser zoom at 90–100% and close notifications and unrelated tabs.

## 0:00–0:16 — Hook

**Screen:** Hero and three principles.

**Voiceover:**

> Most AI decision tools give a team one confident answer. Dissent Garden keeps
> the disagreement you cannot afford to lose, binds it to evidence, and turns it
> into the next reversible test.

## 0:16–0:36 — Plant a decision

**Screen:** Scroll through the loaded staged-rollout decision and five evidence
items. Pause on the Android crash regression and lack of weekend support.

**Voiceover:**

> Here is a real product choice: launch onboarding to everyone, or stage it at
> ten percent. These stable evidence IDs are the only facts the model may cite.
> Anything else must remain an inference.

## 0:36–0:58 — Codex and GPT-5.6

**Screen:** Select **Convene the garden**. Cut the wait to a brief montage of the
four processing stages plus Codex running the tests.

**Voiceover:**

> Codex helped build and verify the entire product: contracts, interface,
> failure boundaries, browser QA, and seventeen tests. At runtime, GPT-5.6 Sol
> runs Builder, Breaker, and Grounder in isolation and in parallel. A fourth
> GPT-5.6 pass adjudicates only after all three are complete.

## 0:58–1:30 — Evidence-bound result

**Screen:** Show the surviving decision, seat theses, and one claim in each
status. Finish on unresolved tension and the cheapest next test.

**Voiceover:**

> Dissent Garden does not vote. Supported claims can survive, live conflicts
> stay disputed, and persuasive claims without supplied evidence are demoted to
> unsupported by the server. The product preserves the most consequential
> tension and proposes the cheapest experiment that could change the decision.

## 1:30–1:57 — Receipt-aware memory

**Screen:** Show the Governor and open decision history. Run the exact decision
again and show `reused`, zero new tokens, and the source receipt.

**Voiceover:**

> The receipt-aware Governor keeps memory from becoming context bloat. This
> exact repeat reuses a verified, correction-free receipt with zero GPT-5.6
> calls. The original live run used 6,766 tokens; the repeat avoids all 6,766.
> A correction appends to history and invalidates stale reuse instead of
> rewriting the past.

## 1:57–2:29 — Plant a Seed

**Screen:** Return to Plant a Seed. Show the one-dollar cap and auto-bloom
boundary, plant the loaded decision, then select **Simulate 30 days**.

**Voiceover:**

> Plant a Seed turns the decision into a bounded living watch. Local checks stay
> free while reality is repetitive and tighten their wake threshold after
> noise. Material contradictions wake the seed. Before any model work, the seed
> must reserve its worst-case cost against both its own dollar ceiling and the
> global token budget. In this thirty-day simulation, twenty-six checks slept,
> five woke, none were false wakes, and no budget was breached.

## 2:29–2:47 — Close

**Screen:** Frame the result board, verified ledger, and nursery together. End on
the project name and public URL.

**Voiceover:**

> Dissent Garden is an evidence-bound decision workspace for teams shipping
> under uncertainty: disagreement that remains useful, memory that gets tighter,
> and agents that must earn the right to spend again.

## Final edit check

- Runtime is under 3:00; ideal is 2:40–2:50.
- The product is visible and legible at normal YouTube playback size.
- The spoken audio explicitly names both Codex and GPT-5.6.
- The YouTube upload is set to **Public**.
- The closing URL exactly matches the Devpost testing URL.
