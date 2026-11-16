# Mend Financial Platform — Status Report

**Generated At:** 2026-11-16T19:42:00+05:30  
**Git Branch:** `consolidate-fastapi`  
**Latest Commit:** `1774039369f82d1921356bb012572242095f9d45`  
**Commit Author:** `gowthame23 <gowthame23@users.noreply.github.com>`  
**Repository Target:** `https://github.com/gowthame23/medu`  

---

## 1. System Health & Verification Summary

| Verification Gate | Command | Status | Result / Notes |
| :--- | :--- | :--- | :--- |
| **Backend Test Suite** | `python -m pytest -q` | **PASS** | **19 passed, 0 failed, 0 warnings** in 4.02s |
| **TypeScript Typecheck** | `npx tsc --noEmit` | **PASS** | **Exit Code 0** (0 errors) |
| **ESLint Linter** | `npm run lint` | **PASS** | **Exit Code 0** (0 errors, 0 warnings) |
| **Frontend Smoke Test** | `node scripts/smoke_test.mjs` | **PASS** | **Exit Code 0** (0 parseFloat, CSP strict, routes intact) |
| **Production Build** | `npm run build` | **PASS** | **Exit Code 0** (Turbopack static prerender of `/`, `/_not-found`, `/login`, `/register`) |
| **Git Working Tree** | `git status` | **CLEAN** | Working tree clean, 91 files committed on branch |

---

## 2. Architecture & Single Source of Truth

- **Authoritative Backend**: FastAPI core running on `/api/v1` handles 100% of business logic, Argon2id auth, JWT rotation, Decimal money arithmetic, and database state.
- **Legacy Backends Deleted**: Next.js mock API routes (`src/app/api/*`), in-memory store (`src/lib/dataStore.ts`), duplicate Express server (`server/`), and unused Prisma schema have been completely removed.
- **Frontend Integration**: Next.js App Router reverse-proxies `/api/v1/*` to the FastAPI backend via `rewrites()` in `next.config.ts`, maintaining a single-origin perimeter.
- **In-Memory JWT Access Tokens**: Stored only in browser JavaScript memory; never persisted in `localStorage` or `sessionStorage`.
- **Rotating Refresh Tokens**: Transported via `httpOnly`, `SameSite=Lax` cookies with dynamic `secure=True` in production. Rotated on every use with a 30-second concurrency grace window to accommodate React StrictMode in development.

---

## 3. Security & Integrity Audit Status

### A. Authentication & User Management
- **Argon2id Password Hashing**: Resistant to GPU/ASIC cracking.
- **Enumeration-Safe Login**: Dummy Argon2id hash computation on non-existent emails eliminates timing-based account enumeration.
- **Enumeration-Safe Registration**: Constant-time execution returning a uniform HTTP 201 response with synthetic pseudo-random UUIDs and fresh timestamps, preventing real UUID or account age leakage.
- **Session Revocation**: `POST /auth/change-password` and `POST /auth/logout-all` immediately invalidate all active refresh tokens for the user account.
- **Timezone Validation**: Strict IANA timezone validation via Python's standard `zoneinfo.available_timezones()`.

### B. Network & CSRF Protections
- **Origin / Referer Verification**: Mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) are checked against allowed `CORS_ORIGINS`. In production, requests lacking Origin/Referer headers are rejected with `403 Forbidden`. Localhost/testserver exemptions are strictly disabled in production.
- **Strict Content Security Policy (CSP)**: In production, `script-src` is strictly `'self'` without `'unsafe-eval'` or `'unsafe-inline'`. Dev exemptions are gated behind `isDev`. HSTS is configured with `max-age=31536000; includeSubDomains`.
- **Bounded Rate Limiter**: Sliding-window in-memory rate limiting applied to `POST /auth/login` (5/min), `POST /auth/register` (5/min), `POST /auth/refresh` (30/min), and `POST /invitations/accept` (10/min). IP resolution strictly checks `settings.TRUSTED_PROXIES` before evaluating `X-Forwarded-For` to prevent header spoofing. Storage is capped at 10,000 keys with LRU/FIFO eviction.

### C. Payment Lifecycle & Concurrency
- **Row-Level Concurrency Locking**: `pay_bill()` and `settle_self_reported_payment()` lock bill rows using `SELECT ... FOR UPDATE`, preventing race conditions.
- **Partial Unique Indexes**: Enforces `UNIQUE(bill_id) WHERE status IN ('PENDING', 'SUCCESS')` with both PostgreSQL and SQLite dialect support (`postgresql_where` and `sqlite_where`).
- **Client Idempotency Keys**: Enforces `crypto.randomUUID()` client tokens scoped to `(bill_id, idempotency_key)` with unique DB constraint.
- **Payment Cancellation**: `POST /bills/{id}/payment/cancel` marks pending transactions as `FAILED` (`CANCELLED_BY_USER`), releasing row locks for immediate retry.
- **Self-Reported Payment Safety**: `POST /bills/{id}/mark-paid` transitions bills to `PAID_UNVERIFIED` with `verified_timestamp=None`, rejects already paid or deleted bills, and spawns the next recurring bill instance.
- **Webhook Gateway Security**: `POST /api/v1/payments/webhook` enforces HMAC-SHA256 signature verification with a 300s replay window, validates payload `amount` against database transaction amount, and deduplicates events via indexed `UNIQUE(event_id)` DB constraint in `payment_events`.
- **Outbox Worker**: Polled with `SELECT ... FOR UPDATE SKIP LOCKED` and exponential backoff retry (up to 5 attempts).

### D. Liabilities Vault & Privacy Isolation
- **100% Private Liabilities**: Loans, prepayments, and amortization schedules are strictly keyed to `user_id` with zero family foreign keys. Invisible across family boundaries.
- **Dynamic Principal & Prepayments**: `POST /loans/{id}/payments`, `POST /loans/{id}/prepayments` (reducing tenure or EMI), and `PATCH /loans/{id}` recalculate balances and daily interest costs dynamically.
- **Zero Float Money**: Zero `parseFloat` in frontend code; all amounts handled as exact decimal strings or integer paise. Python backend uses `Decimal` with fixed-point `Numeric(14, 2)` database columns.
- **Immediate Family Access Revocation**: Removing a member immediately revokes access to all family radar and bill endpoints (returning 404).

---

## 4. Test Suite Execution Details (19 Pytest Tests)

1. `test_register_and_login_flow`: User registration, Argon2id hashing, JWT access token, and refresh token cookie issue.
2. `test_registration_enumeration_safe`: Constant-time execution; hides real UUID and account age on duplicate email.
3. `test_invalid_timezone_validation`: Rejection of non-IANA timezones with HTTP 422.
4. `test_rate_limiting_login`: Sliding-window limiter triggering HTTP 429 on rapid attempts.
5. `test_origin_csrf_check`: Rejection of unauthorized origins and missing origins in production with HTTP 403.
6. `test_production_guards_against_insecure_secrets`: Fail-fast rejection if default dev secrets or short keys are used in production.
7. `test_family_lifecycle_and_privacy`: Strict family invitation email-binding and role enforcement.
8. `test_financial_precision_and_no_float`: Zero floating-point rounding drift across `Decimal` and `Numeric(14, 2)`.
9. `test_emi_reference_math`: Exact loan EMI formula matching standard reference tables with terminal zero balance.
10. `test_liability_api_endpoints`: Dynamic principal decrementing via `/payments` and `/prepayments`, recalculation of daily cost, and `PATCH /loans/{id}` interest updates.
11. `test_alembic_migrations_from_scratch`: Clean database instantiation via `alembic upgrade head`, validating all 19 tables, `payment_events.event_id`, and partial unique indexes.
12. `test_payment_idempotency_and_settlement`: Client UUID idempotency deduplication returning stored transactions.
13. `test_concurrent_payment_race_condition`: Simultaneous concurrent payment requests via `asyncio.gather` verifying row-level isolation (exactly one 200 SUCCESS, one 409 Conflict).
14. `test_mark_paid_safety_and_rejection`: Self-reported payments locking rows, marking `PAID_UNVERIFIED`, rejecting subsequent payments, and rejecting deleted bills.
15. `test_payment_webhook_and_ledger`: HMAC-SHA256 signature verification, transaction transition, amount validation, outbox generation, and ledger deduplication against replays.
16. `test_payment_cancellation`: User-initiated cancellation of pending payment intents releasing locks for immediate re-attempt.
17. `test_zero_debt_leakage_in_family`: 100% private liabilities vault data completely invisible across family member boundaries.
18. `test_radar_and_range_queries`: 7-day radar filtering out paid bills and date-range log retrieval.
19. `test_extended_privacy_and_isolation_matrix`: Multi-account isolation proving zero leakage across Personal Radar, Daily Notes/Categories, Loan Vault, and Immediate Family Access Revocation upon removal.

---

## 5. Next Steps
1. Push branch `consolidate-fastapi` to remote `https://github.com/gowthame23/medu`.
2. Monitor GitHub Actions CI run (`.github/workflows/ci.yml`) with PostgreSQL service.
3. Review and merge into `main` when ready.
