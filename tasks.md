# Mend Financial Platform — Task Tracker

> **File Policy**: This file tracks active, completed, and upcoming tasks. It is updated whenever tasks change, new requirements arrive, or work items are completed.

---

## Current Status Overview
- **Working Branch**: `consolidate-fastapi`
- **Latest Commit**: `acc99ba` (`gowthame23 <gowthame23@users.noreply.github.com>`)
- **Pytest**: 19 Passed, 0 Warnings
- **TypeScript**: 0 Errors (`tsc --noEmit`)
- **ESLint**: 0 Errors, 0 Warnings (`eslint`)
- **Smoke Test**: Passed (`node scripts/smoke_test.mjs`)
- **Turbopack Build**: Passed (`next build`)

---

## 1. Completed Tasks

### Phase 1 — Consolidation on FastAPI
- [x] Delete Next.js mock API routes (`src/app/api/*`).
- [x] Delete Next.js mock in-memory data store (`src/lib/dataStore.ts`).
- [x] Delete duplicate Express server (`server/index.js`).
- [x] Remove unused Prisma schema and configuration (`prisma/`, `prisma.config.ts`).
- [x] Create typed API client (`src/lib/api.ts`) targeting FastAPI `/api/v1` base URL.
- [x] Implement in-memory JWT access token management (never stored in localStorage).
- [x] Configure Next.js rewrites proxying `/api/v1/*` to FastAPI backend.
- [x] Add user authentication UI (`/login` and `/register` pages).
- [x] Create `AuthContext` with silent refresh on application mount.
- [x] Implement 30-second refresh token rotation grace window for React StrictMode compatibility.

### Phase 2 — Database Schema & Migrations
- [x] Initialize Alembic environment in `backend/alembic/`.
- [x] Create initial schema migration `0fa0163424e7_initial_schema.py` covering all 19 database models.
- [x] Enforce partial unique index `uq_bill_active_payment` with dual PostgreSQL and SQLite dialect support (`postgresql_where` and `sqlite_where`).
- [x] Fix Alembic migration runner to support explicit `DATABASE_URL` environment variables.
- [x] Add automated test `test_alembic_migrations_from_scratch` verifying migration from head down.

### Phase 3 — Authentication & Network Security Hardening
- [x] Implement constant-time login check using dummy Argon2id hash on invalid email queries.
- [x] Implement enumeration-safe registration: constant-time Argon2 hash returning uniform 201 response with synthetic pseudo-random UUIDs and fresh timestamps.
- [x] Implement sliding-window rate limiter on `POST /auth/login` (5/min), `POST /auth/register` (5/min), `POST /auth/refresh` (30/min), and `POST /invitations/accept` (10/min).
- [x] Restrict `X-Forwarded-For` inspection to direct clients in `settings.TRUSTED_PROXIES` to prevent spoofing bypasses.
- [x] Bound rate limiter memory to 10,000 tracked keys with FIFO/LRU eviction.
- [x] Create CSRF / Origin verification middleware rejecting untrusted origins and rejecting missing Origin/Referer headers in production.
- [x] Disable localhost/testserver origin exemptions in production (`APP_ENV=production`).
- [x] Configure dynamic `secure=True` cookie setting for refresh tokens in production or over HTTPS.
- [x] Default `DEBUG = False` in application settings.
- [x] Disable interactive docs (`/docs`, `/redoc`, `/openapi.json`) in production.
- [x] Validate IANA timezones via Python standard library `zoneinfo.available_timezones()`.
- [x] Add production startup guards refusing to start if `ENABLE_SANDBOX_PAYMENTS=True` or if `SECRET_KEY` / `WEBHOOK_SECRET` are insecure defaults.

### Phase 4 — Payment Lifecycle & Concurrency Guards
- [x] Wrap `POST /bills/{id}/mark-paid` inside `PaymentService.settle_self_reported_payment()` with `SELECT ... FOR UPDATE` row locking.
- [x] Ensure `/mark-paid` and `/pay` reject both `PAID` and `PAID_UNVERIFIED` bills with `409 ALREADY_PAID`.
- [x] Reject mark-paid attempts on deleted (soft-deleted) bills with 404.
- [x] Implement payment cancellation endpoint `POST /bills/{id}/payment/cancel` releasing pending bill locks.
- [x] Create webhook route `POST /api/v1/payments/webhook` with HMAC-SHA256 signature verification and 300s replay window.
- [x] Enforce webhook business amount check: payload `amount` must match `txn.amount` or returns `400 Bad Request`.
- [x] Add `event_id` column to `PaymentEvent` with indexed `UNIQUE(event_id)` DB constraint for ledger deduplication under concurrent deliveries.
- [x] Update transactional outbox publisher with `SELECT ... FOR UPDATE SKIP LOCKED` and exponential backoff retry.
- [x] Remove duplicate `AuditRepository` from `backend/app/repositories/outbox.py`.
- [x] Define explicit `BillCategory` and `RecurrenceInterval` enums in bill schemas.

### Phase 5 — Dynamic Liabilities & Precision Money
- [x] Add `POST /api/v1/loans/{id}/payments` to record regular EMI payments and decrement remaining principal.
- [x] Add `POST /api/v1/loans/{id}/prepayments` supporting lump-sum prepayments (`REDUCE_TENURE` and `REDUCE_EMI`).
- [x] Add `PATCH /api/v1/loans/{id}` to update loan details and recalculate EMI schedules.
- [x] Implement dynamic calculation of `remaining_principal` and daily debt interest costs.
- [x] Completely eliminate `parseFloat` and `Math.random` from frontend code in `src/`.
- [x] Enforce exact integer paise arithmetic and decimal string validation in frontend forms.
- [x] Enforce strict 100% privacy boundary: loans, prepayments, and amortization schedules are completely invisible across family boundaries.
- [x] Verify multi-account isolation and immediate 404 family access termination upon member deletion.

### Phase 6 — Infrastructure, Smoke Testing & Policy
- [x] Configure strict Next.js Content Security Policy (CSP) in `next.config.ts` without `'unsafe-eval'` or `'unsafe-inline'` in production.
- [x] Calibrate HSTS header to `max-age=31536000; includeSubDomains`.
- [x] Parameterize `SECRET_KEY`, `WEBHOOK_SECRET`, and `POSTGRES_PASSWORD` in `docker-compose.yml`.
- [x] Create `.env.example` with secure configuration guidance.
- [x] Create frontend smoke test suite (`scripts/smoke_test.mjs`) checking zero float, strict CSP, and route integrity.
- [x] Wire `npm test` to run `tsc --noEmit && eslint && node scripts/smoke_test.mjs`.
- [x] Align `README.md` and `SECURITY.md` with exact implementation.
- [x] Commit all changes to branch `consolidate-fastapi` under sole contributor attribution `gowthame23 <gowthame23@users.noreply.github.com>`.

---

## 2. Active & Next Tasks

- [ ] **Task 2.1 — Push to Remote Repository**:
  - Push branch `consolidate-fastapi` to `https://github.com/gowthame23/medu`.
  - Ensure commit attribution matches `gowthame23 <gowthame23@users.noreply.github.com>`.

- [ ] **Task 2.2 — GitHub Actions CI Verification**:
  - Trigger and monitor `.github/workflows/ci.yml` run on GitHub.
  - Verify full test suite execution against PostgreSQL 16 Alpine service container.

- [ ] **Task 2.3 — Branch Review & Merge**:
  - Create Pull Request from `consolidate-fastapi` into `main`.
  - Review diff and merge cleanly.

- [ ] **Task 2.4 — Live Deployment & Staging Verification**:
  - Test live container build with `docker compose up --build` on a Docker-enabled host.
  - Run database migration entrypoint (`alembic upgrade head`) against production PostgreSQL.
