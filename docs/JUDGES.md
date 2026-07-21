# Judge Test Path

Dissent Garden supports a no-key showcase and a live GPT-5.6 path. The public
deployment supplied in Devpost intentionally uses the safe showcase path so a
public URL cannot spend the creator's API balance.

## 60-second showcase — no key

1. Open the public showcase URL from the Devpost entry.
2. Select **Use staged rollout example**.
3. Select **Watch showcase**.
4. Inspect the surviving decision, three isolated seat theses, claim status
   board, unresolved tension, and cheapest next test.
5. Return to **Plant a Seed**, keep the $1 ceiling, and select
   **Plant current decision**.
6. Select **Simulate 30 days**. Expected: 26 quiet checks, 5 wakes, 0% false
   wakes, $0.545 simulated spend, 0 budget breaches, verified ledger.
7. Open **Decision history** to inspect the verified append-only chain.

The showcase is always labeled. It never claims to be a live model response and
never satisfies live receipt reuse.

## Live GPT-5.6 path

Supported platforms: Windows 10/11, macOS, Linux, or Docker with Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set `OPENAI_API_KEY` in the same shell, then run:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`, load the staged rollout example, and select
**Convene the garden**. A successful run should report model
`gpt-5.6-sol`, write one verified decision receipt, and show actual input/output
usage. Running the exact same untouched request again should reuse the verified
receipt with zero provider calls. Appending a correction invalidates that exact
reuse path.

## Automated verification

```bash
python -m pytest -q
python -m compileall -q app tests
node --check app/static/app.js
```

The test suite makes no paid OpenAI calls. The recorded live run is documented
in `docs/LIVE_TEST_2026-07-21.md`.

## Data boundary

API keys are environment-only. Local decisions are ignored by Git. The hosted
showcase has no API key and uses ephemeral storage. Dissent Garden is a
single-user contest prototype; public multi-tenant use is deliberately out of
scope until authentication and tenant isolation are added.
