# Submission-Day Checklist

Official deadline: **July 21, 2026 at 5:00 PM Pacific**. Aim to submit by
**4:30 PM Pacific** so account, upload, or form errors do not become fatal.
The current official rules are at <https://openai.devpost.com/rules>.

## Already complete in the repository

- [x] New Build Week implementation with timestamped Git history
- [x] Required GPT-5.6 Sol runtime through the Responses API
- [x] Complete product experience and safe no-key showcase
- [x] Plant a Seed longitudinal differentiator and hard budget enforcement
- [x] Seventeen automated tests and successful live model verification
- [x] MIT license and ignored keys/private runtime data
- [x] Windows, macOS, Linux, Docker, CI, and deployment instructions
- [x] Paste-ready Devpost description and sub-three-minute recording script
- [x] Judge testing path and Codex collaboration evidence

## Account-owned actions required before submission

- [ ] Confirm entrant eligibility and click **Join Hackathon** on Devpost.
- [x] Publish this repository: <https://github.com/vanzantium/dissent-garden>.
- [x] Deploy the public showcase: <https://dissent-garden.onrender.com>.
- [x] Record the scripted demo with English audio, keep it under three minutes,
  and upload it publicly to YouTube: <https://youtu.be/UlaSAha0Swk>.
- [ ] Run `/feedback` in the primary Codex build task and paste the Session ID.
- [ ] Upload the cover image and at least one product screenshot.
- [ ] Paste the fields from `docs/SUBMISSION_DRAFT.md` and choose
  **Work and Productivity**.
- [ ] Test every submitted URL in a private/incognito browser.
- [ ] Submit on Devpost and verify the project appears as submitted before
  5:00 PM Pacific.

## Video compliance gate

- [x] Duration is 2:39 and definitely under 3:00.
- [x] Audio clearly explains what was built and how Codex and GPT-5.6 were used.
- [x] The video visibly demonstrates the working product.
- [x] No copyrighted music, third-party logos, private corpus text, personal
  decisions, API keys, billing pages, email addresses, or other private data.
- [x] YouTube visibility is **Public**, not Unlisted or Private.

## Final technical gate

```powershell
python -m pytest -q
python -m compileall -q app tests
node --check app\static\app.js
git diff --check
```

Expected test result: `17 passed`.
