# Dissent Garden

> Keep the disagreement you cannot afford to lose.

![Dissent Garden — evidence-bound decisions and budgeted growth](docs/assets/dissent-garden-cover.png)

Dissent Garden is an evidence-bound decision workspace for product and
engineering teams shipping under uncertainty. Three role-separated GPT-5.6
passes examine the same decision before an arbiter sees their work:

- **Builder** finds the strongest bounded, reversible proposal.
- **Breaker** exposes failure modes, silent assumptions, and displaced cost.
- **Grounder** audits claims against the evidence and constraints supplied.
- **Arbiter** separates claims that survived, remain disputed, or lack support.

The product does not average the seats or manufacture consensus. It preserves
the most important unresolved tension, recommends the cheapest reversible test,
and records the result in a hash-chained append-only ledger.

## Why it exists

Most AI decision tools return one persuasive answer. That can hide minority
risks, unsupported claims, and the reasons a decision changed later. Dissent
Garden makes those boundaries visible:

1. Role-separated seats reason in isolation before adjudication.
2. Model-supplied evidence IDs are validated by the server.
3. Unsupported claims cannot be silently promoted as survivors.
4. Corrections append to history rather than rewriting it.
5. A Token Governor prevents the ledger itself from becoming context bloat.

## Judge in 60 seconds

No API key is required for the safe judging path:

1. Launch the app and select **Use staged rollout example**.
2. Select **Watch showcase** to inspect the complete, clearly labeled result.
3. Review survived, disputed, and unsupported claims plus the unresolved tension.
4. Plant the loaded decision as a seed, then select **Simulate 30 days**.
5. Open **Decision history** to verify the append-only receipt chain.

For live evaluation, set `OPENAI_API_KEY` and select **Convene the garden**. The
same sample was validated end-to-end with GPT-5.6 Sol; the measured run and
receipt-reuse proof are recorded in
[`docs/LIVE_TEST_2026-07-21.md`](docs/LIVE_TEST_2026-07-21.md). A more detailed
test path is in [`docs/JUDGES.md`](docs/JUDGES.md).

| Evidence-bound result | Bounded longitudinal watch |
| --- | --- |
| ![Dissent Garden result board](docs/assets/dissent-garden-result.jpg) | ![Plant a Seed nursery](docs/assets/dissent-garden-seed.jpg) |

## Token Governor

The receipt-aware Governor is part of the product, not a future optimization.

- Exact repeats of a live, verified, correction-free decision reuse its receipt
  with **zero new GPT-5.6 calls**. The displayed saving comes from the original
  receipt's actual recorded usage.
- A later correction invalidates exact reuse and enters the next bounded memory
  brief, so updated evidence cannot silently return a stale verdict.
- Near-relevant prior decisions are ranked lexically and condensed into a brief
  capped at 1,800 characters.
- Old conclusions are explicitly not treated as new evidence.
- The arbiter is told to foreground changed evidence, new dissent, or a truly
  different next test.
- BUILD, AUDIT, DWELL, and SHED modes progressively reduce output ceilings as
  the configurable daily budget fills.
- Actual input/output usage and actual model tokens avoided by receipt reuse are
  written to a separate local Governor state file and displayed in the
  interface. Hypothetical context reduction is labeled separately as estimated.
- Curated showcase records never enter live model memory or satisfy live cache
  reuse.

This is bounded, auditable compression—not an ever-growing hidden summary.

## Plant a Seed

A seed turns one decision into a bounded longitudinal watch. It stores a dollar
ceiling, expiry, check rhythm, evidence versions, wake/sleep history, and every
budget reservation in a separate hash-chained event ledger.

- Local checks use deterministic novelty, relevance, and contradiction signals
  and make no OpenAI request.
- Exact duplicate evidence is rejected because repetition is not new evidence.
- Quiet checks raise the future wake threshold; relevant contradictory evidence
  can wake the seed immediately.
- A fresh GPT-5.6 bloom must reserve its conservative worst-case token and USD
  exposure against both the global daily budget and the seed budget before the
  first provider call.
- Auto-bloom is opt-in and operates only while this local server and its
  environment-held API key remain active. It never gathers external evidence or
  performs external actions.
- Harvesting stops the seed while preserving its full event history.

The nursery includes a zero-API 30-day simulator for testing false wakes,
budget breaches, spend, sleeps, and hash-chain validity.

## Quick start

Requires Python 3.11+.

```powershell
python -m pip install -r requirements.txt
.\run.ps1
```

If `OPENAI_API_KEY` is not already set, the launcher asks you to copy the key to
the clipboard and press Enter. It validates the key shape, transfers the key
only to the server process, and immediately clears the clipboard. The key is not
written to disk. You may alternatively set `$env:OPENAI_API_KEY` in the same
PowerShell session before launching. On
its first run, the launcher creates an ignored project-local `.venv` and installs
the pinned dependency ranges there, preventing conflicts between system Python
installations.

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

On Windows you can also double-click `run.bat`. The interface remains usable
without an API key through the clearly labeled **Watch showcase** path. Showcase
mode demonstrates the complete UI with a curated dataset; it never claims to be
a live model response.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Set `OPENAI_API_KEY` in the same shell before the final command to enable live
deliberation. Without it, the public-safe showcase remains fully usable.

### Docker or hosted showcase

```bash
docker build -t dissent-garden .
docker run --rm -p 8765:8765 dissent-garden
```

The included `render.yaml` deploys the same showcase-only image on Render's free
web-service plan. It intentionally omits `OPENAI_API_KEY`, so a public demo
cannot consume paid model tokens. Add the key as a secret environment variable
only for a controlled deployment. Render and other hosts may supply `PORT`; the
container honors it automatically.

### Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | none | Enables live deliberation |
| `DISSENT_GARDEN_MODEL` | `gpt-5.6-sol` | Explicit GPT-5.6 Sol runtime model for Build Week |
| `DISSENT_GARDEN_INPUT_USD_PER_MILLION` | model default (`5` for Sol) | Input rate used by hard USD reservations |
| `DISSENT_GARDEN_OUTPUT_USD_PER_MILLION` | model default (`30` for Sol) | Output rate used by hard USD reservations |
| `DISSENT_GARDEN_DAILY_TOKEN_BUDGET` | `100000` | Local Governor threshold |
| `DISSENT_GARDEN_API_TIMEOUT_SECONDS` | `90` | Timeout applied by the OpenAI client |
| `DISSENT_GARDEN_API_MAX_RETRIES` | `2` | SDK retries for transient failures |
| `DISSENT_GARDEN_SEED_AUTOPILOT_SECONDS` | `60` | Interval for due opt-in auto-bloom seeds |
| `DISSENT_GARDEN_DATA_DIR` | project `data/` | Writable ledger location for isolated demos or hosted storage |

## Architecture

```mermaid
flowchart LR
    D[Decision + constraints + evidence] --> G[Token Governor]
    S[Planted seed + evidence deltas] --> W[Deterministic wake gate]
    W -->|quiet| Q[Sleep with stronger backoff]
    W -->|material| G
    G -->|exact fingerprint| R[Reuse verified receipt]
    G -->|fresh or changed| B[Builder]
    G --> K[Breaker]
    G --> O[Grounder]
    B --> A[GPT-5.6 Arbiter]
    K --> A
    O --> A
    M[Bounded relevant receipt brief] --> A
    A --> C[Survived / disputed / unsupported claims]
    C --> L[Hash-chained ledger]
    L --> M
```

The three role-separated passes run concurrently through the OpenAI Responses API. Each returns
strict structured output. The arbiter receives their completed isolated
passes and, when relevant, a small receipt brief produced deterministically by
the Governor. Server-side validation removes invented evidence IDs and demotes
evidence-free survivors to unsupported.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /api/health` | Runtime, model, ledger, and Governor status |
| `GET /api/sample` | Editable demonstration request |
| `POST /api/showcase` | Clearly labeled curated UI showcase |
| `POST /api/deliberate` | Live four-pass GPT-5.6 deliberation |
| `GET /api/ledger` | Verified append-only decision history |
| `GET /api/governor` | Token budget, usage, savings, and recent events |
| `POST /api/decisions/{id}/corrections` | Append a correction without erasing history |
| `GET/POST /api/seeds` | List or plant bounded living decisions |
| `POST /api/seeds/{id}/evidence` | Append a versioned observation |
| `POST /api/seeds/{id}/check` | Check locally or bloom if the gate wakes |
| `POST /api/seeds/{id}/harvest` | Stop work without erasing seed history |
| `POST /api/seeds/simulate` | Run the deterministic longitudinal harness |

## Verification

```powershell
python -m pytest -q
python -m compileall -q app tests
node --check app\static\app.js
```

The tests cover the front door, showcase contract, missing-key boundary,
evidence-ID validation, hash-chain tamper detection, correction-aware live-only
receipt reuse, canonical fingerprints, bounded memory compaction, Governor
accounting, orphan-correction rejection, hard reservation denial, seed
deduplication, material wake-ups, zero-cost checks, and longitudinal budget
safety.

## OpenAI Build Week disclosure

This repository and implementation were created on **July 17, 2026**, during
the OpenAI Build Week submission period. The conceptual roots—role-separated
personas, preserved disagreement, append-only ledgers, and token governance—were
developed earlier in the creator's private research corpus. No pre-existing
application code was copied into this repository. The Build Week project is the
new product design, GPT-5.6 orchestration, receipt-aware Governor, web interface,
testing, and submission package contained here.

### How Codex was used

Codex was the primary development environment and accelerated the project from
rules analysis through live verification. It was used for:

- product framing and contest-rule analysis;
- architecture and data-contract design;
- GPT-5.6 Responses API integration;
- backend, UI, ledger, and Token Governor implementation;
- automated tests and live browser verification;
- responsive design review and submission documentation.

The creator made the central product decisions: focus on product and engineering
teams; reject majority voting; preserve consequential dissent; require stable
evidence IDs; keep corrections append-only; and make longitudinal monitoring
fail closed against explicit token and dollar ceilings. Codex challenged those
choices from the judges', operator's, and end user's perspectives, then helped
translate them into contracts, validation, tests, and the final interface.

Timestamped commits and a capability-by-capability build record are collected in
[`docs/CODEX_BUILD_EVIDENCE.md`](docs/CODEX_BUILD_EVIDENCE.md).

The `/feedback` session ID from this primary build task will be added to the
Devpost submission.

### How GPT-5.6 is used in the product

GPT-5.6 performs the product's core work at runtime. Three role-separated calls
produce evidence-cited seat passes before seeing one another. A fourth call adjudicates their atomic
claims and creates the surviving core, unresolved tension, next test, and
decision. Removing GPT-5.6 would remove the deliberation product itself; its use
is neither incidental nor decorative.

## Data and safety boundaries

- API keys are read only from the environment and are never stored.
- Decision records remain local as JSONL unless the operator deploys the app.
- Evidence is supplied by the user; Dissent Garden does not claim to fact-check
  the external world.
- The claim-survival rate reports the share of adjudicated claims that survived;
  it is not a confidence or truth score.
- The hash chain is tamper-evident, not tamper-proof against a privileged local
  attacker who can replace the complete ledger.
- The current JSONL build is a single-user contest prototype. Public deployments
  should contain demonstration data only until authentication and tenant
  isolation are added.
- Dissent Garden is a decision aid, not medical, legal, or financial advice.

## License

MIT — see `LICENSE`.
