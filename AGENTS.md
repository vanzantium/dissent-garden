# Dissent Garden Build Rules

This repository is the new OpenAI Build Week entry begun July 17, 2026.

- Keep the product narrow: evidence-bound decisions, preserved dissent, reversible next tests.
- The real runtime model must remain GPT-5.6 for the contest submission.
- Showcase mode must always be visibly labeled and must never masquerade as a live model call.
- Never invent evidence IDs. Validate every model-supplied citation server-side.
- Decision history is append-only. Corrections are new records, never rewrites.
- Do not commit API keys, private brain-corpus material, or personal decision data.
- Run `python -m pytest -q` after backend changes.
- Verify the complete browser flow at `http://127.0.0.1:8765` after UI changes.

