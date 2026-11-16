# TASK.md — Round 3 (written by Claude Code; fully replaced every round)

Implementer: Antigravity. Reviewer/commander: Claude Code.
When done, OVERWRITE `REPORT.md` (delete the old content, write the new report). Exactly one file named `REPORT.md`.

## Rules
1. Read `AGENTS.md` first. This Next.js version has breaking changes: read `node_modules/next/dist/docs/` before changing Next.js code.
2. Do NOT edit `TASK.md` or `session.md`. Claude Code owns them.
3. Work the items in order. After each item run the global checks. If a check fails and you cannot fix it, STOP and record it in `REPORT.md`.
4. Architecture: routers -> services -> repositories; money is Decimal in Python and strings in JSON/TS; outsiders get 404.
5. Commit after each passing item on `consolidate-fastapi`: `task(N): <title>`. Never commit a failing state. Do NOT push; the user pushes.
6. No claims without evidence. Paste REAL command output. Write "NOT RUN" plus the reason for anything you could not run. Run `git status --short` at the end and paste it.
7. Do not add features not listed. If ambiguous, write the question in `REPORT.md` and stop.
8. Never edit an applied Alembic migration. Schema changes are NEW revisions only.

## Global checks (after every item)
```
python -m pytest -q
npx tsc --noEmit
npm run lint
npm run build
```

## Items

### 1. Webhook error handling must not lose payments
In `backend/app/api/v1/payments.py` the final `except (IntegrityError, OperationalError)` returns 200 `already_processed` for ANY database error. A transient DB failure (deadlock, lost connection) would be acknowledged to the gateway, which then never retries, so a real payment is lost.
- Only a unique-violation on `event_id` may return `already_processed` (after rollback, re-query the ledger for that `event_id` to confirm it exists). Any other `IntegrityError` or `OperationalError` must roll back and return 5xx (503 is fine) so the gateway retries. Never swallow unexpected exceptions.
- `payment.success` must REQUIRE `amount`; a missing/null amount returns 400. Keep the mismatch check.
- Tests: (a) simulated `OperationalError` during commit returns 5xx and the transaction stays `PENDING`; (b) `payment.success` without amount returns 400 and changes nothing; (c) a real duplicate `event_id` still returns `already_processed`.

### 2. CSP must be asserted across the whole real user flow
Round 2 proved zero CSP violations only on `/login`, `/register` and one redirect. `scripts/test_e2e.mjs` does not check CSP at all.
- In `scripts/test_e2e.mjs`, listen to `page.on('console')`, `page.on('pageerror')` and a `securitypolicyviolation` event listener injected with `page.addInitScript`. FAIL the test on any CSP violation anywhere in the journey (register, dashboard, add bill, open pay sheet, pay, logout, login).
- Ignore only the expected unauthenticated 401s from silent refresh; list exactly which console messages are ignored and why.
- `scripts/verify_csp_browser.mjs` hardcodes `channel: "msedge"`; use the same Edge-then-Chromium fallback as `test_e2e.mjs`.
- Next warned that it ignored a lockfile outside the repo (`C:\Users\gowth\package-lock.json`). Set `turbopack.root` in `next.config.ts` to the repo root so the warning disappears. Do not delete the user's file outside the repo.

### 3. Real Postgres proof without Docker
Docker is not installed here, but the suite still has never run on Postgres. Get a real Postgres on this Windows machine by any method that does not need Docker (for example portable PostgreSQL binaries from the official zip, or the `pgserver` pip package installed in a throwaway venv; do NOT add it to `requirements.txt`).
- Run the whole suite with `TEST_DATABASE_URL=postgresql+asyncpg://...` and paste the full output, including that `test_postgres_concurrent_payment_race_condition` ran (not skipped).
- Run `alembic upgrade head` on the empty Postgres database and paste it.
- If it truly cannot be done, write NOT RUN with the exact errors you hit.
- Also change CI triggers so the pipeline runs on every push and on `workflow_dispatch` (currently only pushes to main/master, so this branch would never run CI).

### 4. Reproducible dependencies
`backend/requirements.txt` uses `>=` for everything and includes test tools.
- Pin exact versions of the currently passing environment in `backend/requirements.txt` (runtime only) and move pytest, pytest-asyncio and httpx into `backend/requirements-dev.txt`.
- Update CI and README to install both. Keep the Dockerfile on runtime only.
- Confirm the full suite still passes from a fresh virtual environment built from these files. Paste the output.

### 5. Audit log must actually be written
`AuditRepository` exists but nothing calls it, so any "audit trail" claim is false.
- Write audit entries for: login success/failure (never the password; record email hash or user id, not the raw failed-email string if unknown), refresh-token reuse detection, change-password, logout-all, invitation create/accept, member role change/removal, `mark-paid`, payment success/failure/cancel, webhook processed/ignored.
- Never put passwords, tokens, full consumer numbers, loan names/amounts or any loan detail in audit metadata. Use ids only. Use the same trusted-proxy-aware client IP as the rate limiter.
- Tests: entries are written for each category above; a redaction test proves no secrets/loan data appear in any audit row after a full user journey.
- If an event cannot be wired in this round, say so in `REPORT.md` and keep the docs from claiming it.

### 6. Migration discipline
The baseline migration `0fa0163424e7` was edited in place in earlier rounds (it now contains `event_id` and `anchor_day`). Any database created from the older version would be wrong.
- Do not edit it again.
- Add a test that runs `alembic upgrade head` on an empty database and then asserts Alembic autogenerate finds NO differences from the SQLAlchemy models (`alembic check` or `compare_metadata`). Fix any drift with a NEW revision.
- Add one sentence to `README.md` stating that schema changes require a new revision and baseline edits are forbidden after first deployment.

## Stop condition
When done or blocked, overwrite `REPORT.md` with: status per item, files changed, exact command outputs, anything NOT RUN with reasons, and open questions. Then tell the user "REPORT.md is ready."
