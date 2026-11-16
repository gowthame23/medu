# TASK.md — Round 2 (written by Claude Code; rewritten every round)

Implementer: Antigravity. Reviewer/commander: Claude Code.
When done, OVERWRITE `REPORT.md` (delete the old content, write the new report). Keep exactly one file named `REPORT.md` (uppercase); delete any `report.md` duplicate.

## Rules
1. Read `AGENTS.md` first. This Next.js version has breaking changes: read the relevant guide in `node_modules/next/dist/docs/` before changing Next.js code.
2. Do NOT edit `TASK.md` or `session.md`. Claude Code owns them.
3. Work the items in order. After each item run the global checks. If a check fails and you cannot fix it, STOP and record it in `REPORT.md`.
4. Architecture: routers -> services -> repositories; money is Decimal in Python and strings in JSON/TS; outsiders get 404.
5. Commit after each passing item on `consolidate-fastapi`: `task(N): <title>`. Never commit a failing state. Do not push unless the user says so.
6. No claims without evidence. Paste the REAL output of every command. Write "NOT RUN" with the reason for anything you could not run. Do not write "0 warnings" or "clean" unless the output shows it.
7. Do not add features that are not listed here. If something is ambiguous, write the question in `REPORT.md` and stop.

## Global checks (after every item)
```
python -m pytest -q
npx tsc --noEmit
npm run lint
npm run build
```

## Items

### 1. Production CSP must not break the app (highest risk)
`script-src 'self'` with no `'unsafe-inline'` in production will block Next.js's inline hydration/bootstrap scripts unless nonces or hashes are used. Verify it, do not assume.
- Run `npm run build && npm run start`, open `/login` and `/register` in a headless browser (Playwright), and capture console errors. Report any CSP violation verbatim.
- If scripts are blocked, implement nonce-based CSP the way this Next.js version documents it (read `node_modules/next/dist/docs/` for the current mechanism; in Next 16 this may be `proxy.ts` instead of `middleware.ts`). Dev may keep `unsafe-eval` only when `NODE_ENV !== 'production'`.
- Done when: the production build loads `/login`, a user can log in, and the browser console shows zero CSP violations. Paste the evidence.
- Also make the HSTS value in `next.config.ts` match what REPORT.md says (report said 31536000; the file had 63072000 with `preload`). Remove `preload` unless the user says they will submit the domain.

### 2. Webhook state machine hardening
In `backend/app/api/v1/payments.py`:
- A webhook may only move a transaction from `PENDING` to `SUCCESS`/`FAILED`. Ignore (and record in the ledger) `payment.success` for a transaction that is already `FAILED`/cancelled, or when the bill is already `PAID`/`PAID_UNVERIFIED`. Never create a second active transaction on the same bill (the partial unique index would 500).
- Webhook on a cancelled payment must not mark the bill paid. Write that test.
- The Origin-check exemption must be the exact path `/api/v1/payments/webhook`, not any path ending in `/webhook`.
- Two simultaneous deliveries of the same `event_id` must produce one transition and one `already_processed`; handle the unique-constraint `IntegrityError` by returning `already_processed` rather than 500. Add a test.
- Webhook signing secret must come only from settings; confirm production startup fails with the default secret (test exists, keep it).

### 3. Real end-to-end test (replace the fake "smoke test")
`scripts/smoke_test.mjs` only greps source files. Rename it `scripts/static_checks.mjs` and describe it honestly as a static check.
Add a real Playwright test: register -> login -> dashboard renders -> add a personal bill -> pay it (sandbox) -> bill shows paid/unverified state with attribution -> logout. Script `npm run test:e2e`; it must start the backend (SQLite is fine locally) and the frontend itself. Add it to CI with the Postgres service.

### 4. Postgres and Docker proof (be honest if you cannot run)
- Docker is not installed on the reviewer machine. If it is on yours: run `docker compose config`, then `docker compose up --build`, and paste `docker compose ps`, `curl http://localhost:8000/health` and a login through `http://localhost:3000`.
- Check `docker-compose.yml` line `DEBUG: ${DEBUG:-"false"}`: the default may include literal quote characters and fail pydantic bool parsing. Fix it to `${DEBUG:-false}` and confirm with `docker compose config`.
- If you can run Postgres (Docker or local): run the full pytest suite with `TEST_DATABASE_URL=postgresql+asyncpg://...` and paste the result.
- The concurrency test passes on SQLite, which ignores `FOR UPDATE`, so it does not prove locking. Mark it with a clear note and add a Postgres-only version (`pytest.mark.skipif` on SQLite) that really races two requests. If Postgres is unavailable, write "NOT RUN" with the reason; CI will be the proof.

### 5. Documentation truth pass
Read `README.md`, `SECURITY.md` and `REPORT.md` line by line against the code. Remove or correct anything not implemented or not tested. State limits explicitly: in-memory per-process rate limiter, sandbox payment provider only, no real BBPS/UPI integration, no email verification, no password reset, self-reported payments are unverified. Include exact commands for backend tests, frontend checks, e2e and docker.

### 6. Housekeeping
- One `REPORT.md` only. The previous report claimed "Working tree clean" while `report.md` was untracked: do not repeat that. Run `git status --short` at the end and paste it.

## Stop condition
When done or blocked, overwrite `REPORT.md` with: status per item, files changed, exact command outputs, skipped items marked NOT RUN with reasons, and open questions. Then tell the user "REPORT.md is ready."
