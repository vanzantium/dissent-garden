# Devpost Submission — Paste-Ready Draft

## Project name

Dissent Garden

## Tagline

Keep the disagreement you cannot afford to lose.

## Category

Work and Productivity

## One-line description

Dissent Garden turns a high-stakes product decision into an evidence-bound
verdict, preserved dissent, and a budgeted living watch that spends only when
reality materially changes.

## Links to complete before submission

- Public showcase: <https://dissent-garden.onrender.com>
- Public repository: <https://github.com/vanzantium/dissent-garden>
- Public YouTube demo (2:39): <https://youtu.be/UlaSAha0Swk>
- Primary Codex `/feedback` session ID: `ADD SESSION ID`

## Inspiration

Teams increasingly use AI to make decisions faster, but a single polished
answer can hide minority risks, unsupported assumptions, and the reason a
decision changed. Sending the same question to several agents often makes this
worse: it creates more prose, repeats the same premises, and then averages away
the useful disagreement.

We wanted a decision tool that treats dissent as an asset, evidence as a hard
boundary, and memory as something that should become smaller and more useful
over time.

## What it does

Dissent Garden convenes three isolated GPT-5.6 seats around a decision and the
evidence supplied by the user:

- Builder develops the strongest bounded, reversible proposal.
- Breaker exposes failure modes, silent assumptions, and displaced costs.
- Grounder audits claims against the supplied evidence and constraints.

A fourth GPT-5.6 pass acts as arbiter. It does not vote or average. It separates
atomic claims into survived, disputed, and unsupported; preserves the most
consequential unresolved tension; and recommends the cheapest reversible test
that could change the decision. The server allowlists evidence IDs and demotes
evidence-free survivors, so a persuasive model response cannot silently invent
support.

Every decision enters a hash-chained append-only ledger. Corrections add history
instead of erasing it. A receipt-aware Token Governor reuses exact verified,
correction-free decisions with zero new model calls and condenses only relevant
prior receipts into a bounded brief.

Plant a Seed extends the same decision through time. A seed has a lifetime,
check rhythm, and hard dollar ceiling. Deterministic local checks sleep for free
while evidence is repetitive, tighten their wake threshold after noise, and
wake immediately for material contradictions. Before any new model call, the
system must reserve the conservative worst-case cost against both the seed and
global budgets. Receipts let the seed reuse prior reasoning instead of paying to
repeat it.

## How we built it

- Python, FastAPI, Pydantic, and a dependency-light HTML/CSS/JavaScript client
- OpenAI Responses API with GPT-5.6 Sol and strict structured outputs
- Three concurrent role-separated seat calls followed by one adjudication call
- Server-side citation allowlisting and evidence-free survivor demotion
- SHA-256 hash-chained JSONL decisions, reuse receipts, corrections, and seeds
- Deterministic relevance ranking, bounded context compaction, adaptive output
  caps, hard pre-call reservations, and actual usage accounting
- A zero-API longitudinal simulator for false wakes and budget breaches
- Seventeen automated tests, live GPT-5.6 verification, and browser-based QA
- Reproducible Python 3.11/3.12, Docker, CI, and showcase deployment paths

## How we used Codex

Codex was the primary development environment from competition analysis through
the final submission build. It searched the private concept corpus, challenged
the product from user, judge, safety, cost, and scalability perspectives,
designed the contracts, implemented the backend and interface, integrated the
Responses API, wrote and ran tests, operated the browser for responsive visual
QA, diagnosed Windows launcher problems, and verified the live GPT-5.6 flow.

Codex accelerated the translation from product decisions into working,
testable boundaries. The creator chose the central principles: no majority
vote, stable evidence IDs, append-only corrections, preserved consequential
dissent, reversible next tests, and a longitudinal system that must fail closed
against explicit cost ceilings. Timestamped commits and a detailed build record
are included in the repository.

## How we used GPT-5.6

GPT-5.6 performs the core runtime behavior. Builder, Breaker, and Grounder
produce isolated, evidence-cited role passes before seeing one another. The
GPT-5.6 arbiter then evaluates their completed work, classifies atomic claims,
preserves unresolved dissent, and proposes a reversible test. Removing GPT-5.6
would remove the deliberation product itself; it is not decorative.

Strict structured outputs make the result testable, while deterministic
server-side rules enforce evidence lineage. The live sample run used 6,766 model
tokens and cost approximately $0.108755. Repeating the exact decision then
returned in 84 milliseconds with zero new model calls and 6,766 actual tokens
avoided.

## Challenges we ran into

The first hard problem was preventing “multi-agent debate” from becoming three
styles of the same answer. We isolate all three seats and run them concurrently
before the arbiter sees any of their work.

The second was evidence discipline. Structured output alone does not prove a
citation is real, so the server checks every model-supplied evidence ID against
the request and refuses to promote unsupported survivor claims.

The third was longitudinal cost. A naive agent would wake repeatedly, replay an
ever-growing history, and spend until stopped. Plant a Seed separates a free,
deterministic wake gate from expensive reasoning and requires worst-case budget
reservations before provider calls.

## Accomplishments that we're proud of

- A complete, coherent product experience rather than a prompt wrapper
- Visible evidence lineage and explicit unsupported claims
- Consequential dissent preserved without majority voting
- Corrections that never erase the original record
- Exact receipt reuse measured from real prior model usage
- Living decisions that tighten after noise and fail closed on budget
- A 30-day simulation with 26 quiet checks, 5 material wakes, 0 false wakes,
  and 0 budget breaches
- Separate verified hash chains for decisions and longitudinal seed events
- A curated showcase that cannot masquerade as a live response

## What we learned

Durable AI memory should not mean replaying everything. Receipts are most useful
when they prove what the system can safely skip. We also learned that dissent
becomes actionable when it is paired with the smallest test that could change a
decision, and sustainable when the system must earn the right to spend again.

## What's next for Dissent Garden

- Authenticated team workspaces and durable hosted storage
- Connectors that append source-linked evidence without granting action rights
- Outcome check-ins that measure which claims survived contact with reality
- Calibration of wake thresholds and seat reliability against real decisions
- Exportable decision receipts for product, incident, and governance reviews

## Built with

Codex, GPT-5.6 Sol, OpenAI Responses API, Python, FastAPI, Pydantic, JavaScript,
HTML, CSS, Docker, GitHub Actions, and Render.
