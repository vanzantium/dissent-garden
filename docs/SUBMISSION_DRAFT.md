# Devpost Submission Draft

## Project name

Dissent Garden

## Tagline

Keep the disagreement you cannot afford to lose.

## One-line description

Dissent Garden turns a messy product decision and its evidence into an
auditable decision, preserved dissent, and the next reversible test.

## Category

Work and Productivity

## Inspiration

Teams increasingly use AI to accelerate decisions, but a single polished answer
can hide minority risks, unsupported assumptions, and why the decision changed.
We wanted a decision tool where disagreement remains inspectable and useful.

## What it does

Dissent Garden convenes three role-separated GPT-5.6 passes around a decision
and the evidence supplied by the user. A fourth GPT-5.6 pass does not vote or
average them. It separates atomic claims into survived, disputed, and unsupported;
preserves the most consequential unresolved tension; and recommends the cheapest
reversible experiment that could resolve it.

Every decision enters a hash-chained append-only ledger. Corrections add history
instead of erasing it. A receipt-aware Token Governor reuses exact verified,
correction-free decisions without another model call and condenses only relevant prior receipts
into a bounded memory brief, preventing useful memory from turning into token
bloat or repetitive dissent.

## How we built it

- Python, FastAPI, Pydantic, and a dependency-light HTML/CSS/JavaScript client
- OpenAI Responses API with GPT-5.6 and strict JSON-schema outputs
- Three concurrent role-separated seat calls plus one adjudication call
- Server-side citation allowlisting and survivor demotion when evidence is absent
- SHA-256 hash-chained JSONL decisions, reuse receipts, and corrections
- Deterministic relevance ranking, context compaction, adaptive output caps, and
  actual usage accounting in the Token Governor
- Automated tests plus desktop and mobile browser verification through Codex

## How we used Codex

Codex was the primary build environment. It reviewed the competition rules and
private concept corpus, shaped the winning product boundary, designed the data
contracts, implemented the backend and interface, integrated GPT-5.6, wrote and
ran tests, operated the local browser for visual QA, found a horizontal overflow
bug, and incorporated the receipt-aware Token Governor after product review.

Primary `/feedback` session ID: **ADD BEFORE SUBMISSION**

## How we used GPT-5.6

GPT-5.6 performs the central runtime behavior. Builder, Breaker, and Grounder
produce isolated, evidence-cited role passes. The GPT-5.6 arbiter then evaluates
their completed work, classifies claims, preserves unresolved dissent, and
proposes a reversible test. Strict structured outputs make the result testable;
server-side rules prevent invented evidence IDs from being promoted.

## Challenges

The hardest design problem was preventing “multi-agent debate” from becoming
three different styles of the same answer. We isolate role passes by running
the seats concurrently before the arbiter sees any output. The second challenge
was memory: sending an ever-growing ledger back to the model would undermine the
product. The Token Governor therefore treats receipts as an index, reuses exact
results, ranks relevant history deterministically, and sends only a small brief.

## Accomplishments

- A complete decision experience rather than a prompt wrapper
- Visible evidence lineage and explicit unsupported claims
- Preserved disagreement without majority voting
- Corrections that never erase the original record
- Receipt reuse measured from actual prior model usage
- Correction-aware memory that tightens without silently reviving stale verdicts
- A curated showcase that cannot contaminate or impersonate live model memory

## What we learned

Durable AI memory should not mean replaying everything. Receipts are most useful
when they allow the system to prove what it can safely skip. We also learned that
disagreement becomes actionable when it is paired with the cheapest test that
could change the decision.

## What's next

- Team workspaces with authenticated shared ledgers
- Document ingestion with source-span citations
- Outcome check-ins that measure which claims survived reality
- Empirical calibration of seat and source reliability
- Exportable decision records for product and governance reviews
