# Security & Privacy Policy — Mend Financial Platform

## 1. Architectural Security & Single Source of Truth
Mend strictly consolidates all business logic, financial arithmetic, and access controls into a single backend:
- **FastAPI Core**: The authoritative Python backend running on `/api/v1`.
- **Single-Origin Proxy**: Next.js App Router reverse-proxies `/api/v1/*` to the backend, preventing cross-origin cookie, SameSite, and CSRF vulnerabilities.
- **In-Memory Access Tokens**: JWT access tokens are held exclusively in browser runtime memory. They are **never** persisted to `localStorage`, `sessionStorage`, or readable cookies.
- **Refresh Token Rotation**: Refresh tokens are stored in `httpOnly`, `SameSite=Lax` cookies, rotating on every use with dynamic `secure=True` in production or over HTTPS. A 30-second concurrency grace window allows concurrent React StrictMode mounts without tripping token reuse detectors, while replays outside the window immediately trigger full session chain revocation.
- **Origin / CSRF Verification**: Mutating HTTP requests (`POST`, `PUT`, `PATCH`, `DELETE`) are checked against allowed `CORS_ORIGINS`. In production, requests lacking an `Origin` or `Referer` header are rejected with `403 Forbidden`, and localhost/testserver exemptions are strictly disabled in production.
- **Content Security Policy (CSP)**: In production, `script-src` is restricted strictly to `'self'` without `'unsafe-eval'` or `'unsafe-inline'`. HSTS is configured with `max-age=31536000; includeSubDomains`.
- **Production Hardening**: In production environments (`APP_ENV=production`), interactive API documentation (`/docs`, `/redoc`, `/openapi.json`) is completely disabled, and `DEBUG` defaults to `False`. The application enforces fail-fast startup rejection if `ENABLE_SANDBOX_PAYMENTS=True`, or if `SECRET_KEY` or `WEBHOOK_SECRET` are left with default dev-insecure values or are less than 32 characters.

## 2. Authentication & Account Hardening
- **Argon2id Password Hashing**: Passwords are saved with Argon2id parameters resistant to GPU/ASIC cracking.
- **Constant-Time Login**: When an invalid email address is queried during login, a dummy Argon2id verification cycle is executed to ensure identical response timing and prevent user enumeration.
- **Enumeration-Safe Registration**: Registration performs Argon2 hashing and returns uniform responses (with synthetic identifiers and fresh timestamps) without leaking existing account UUIDs or account age.
- **Rate Limiting**: An in-memory sliding window rate limiter protects sensitive endpoints (`POST /api/v1/auth/login` and `/register` at 5/min, `POST /api/v1/auth/refresh` at 30/min, and `POST /api/v1/invitations/accept` at 10/min). IP resolution only trusts `X-Forwarded-For` from configured `TRUSTED_PROXIES` (preventing header spoofing bypasses) and caps in-memory storage to 10,000 tracked keys.
- **Session Revocation**: `POST /auth/change-password` and `POST /auth/logout-all` immediately invalidate all active refresh tokens for the user account.
- **Timezone Validation**: User and family group timezones are strictly validated against the official IANA database via `zoneinfo.available_timezones()`.

## 3. Strict Dual-Account Privacy Boundary
Mend enforces complete isolation between personal and household spaces:
- **Zero Debt Leakage**: Loans and liabilities vault data are partitioned exclusively by `user_id`. They can **never** be accessed by, queried from, or surfaced in family views, household group summaries, notifications, or audit logs.
- **Exclusive XOR Bill Ownership**: The database enforces `CHECK ((user_id IS NOT NULL AND family_group_id IS NULL) OR (user_id IS NULL AND family_group_id IS NOT NULL))`. A bill is either private or household, never ambiguously shared.
- **Email-Bound Household Invitations**: Invitations to join a household group are strictly validated against the authenticated user's email address. Unauthorized users cannot claim or hijack invitation links.
- **Immediate Family Access Revocation**: Removing a member from a household group immediately revokes their access to all family bills, radar, and audit trails.

## 4. Financial Precision (No Float Arithmetic)
To eliminate IEEE-754 binary floating-point rounding errors and wealth drift:
- Database columns use exact fixed-point `Numeric(14, 2)`.
- Backend Python calculations use `Decimal` with strict bankers' rounding (`ROUND_HALF_UP`).
- Network payloads and TypeScript representations treat all monetary values strictly as strings (e.g., `"2450.00"`).
- Frontend form inputs and aggregations validate against exact decimal strings and integer paise arithmetic, eliminating `parseFloat` across all money operations.

## 5. Payment Safety & Concurrency Guards
- **Row-Level Locking**: Concurrent bill payments execute with `SELECT ... FOR UPDATE` row locks, preventing race conditions.
- **Partial Unique Index**: The database enforces `UNIQUE(bill_id) WHERE status IN ('PENDING', 'SUCCESS')` with both PostgreSQL and SQLite partial index support (`postgresql_where` and `sqlite_where`), guaranteeing double payments can never commit simultaneously.
- **Idempotency Key Scoping**: Every payment intent requires a client-generated UUID `Idempotency-Key` scoped to `(bill_id, idempotency_key)`. Attempting to reuse an existing idempotency key with different financial parameters returns `409 Conflict`.
- **Payment Cancellation**: Active `PENDING` payment intents can be explicitly cancelled (`POST /bills/{id}/payment/cancel`), marking the transaction `FAILED` and releasing the bill lock for immediate re-attempt.
- **Self-Reported Payment Status (`PAID_UNVERIFIED`)**: Bills marked as paid without gateway verification transition to `PAID_UNVERIFIED` with an immutable attribution snapshot, requiring provider verification before clearance while preventing duplicate payment attempts.
- **Webhook Replay Protection & Ledger**: Webhook payloads (`POST /api/v1/payments/webhook`) verify HMAC-SHA256 signatures with constant-time equality checks and a 300-second maximum replay tolerance window. Amounts in webhook payloads are validated against the database transaction amount before transition. Processed event IDs are recorded in `payment_events` with an indexed `UNIQUE(event_id)` database constraint to guarantee deduplication even under concurrent deliveries.
- **Outbox Worker**: Asynchronous notification publishing uses `SELECT ... FOR UPDATE SKIP LOCKED` and exponential backoff retries (up to 5 attempts) to prevent worker contention and notification loss.

## 6. Dynamic Liabilities & Amortization
- **Dynamic Remaining Principal**: Loans support recording periodic payments (`POST /loans/{id}/payments`), lump-sum prepayments (`POST /loans/{id}/prepayments`), and parameter updates (`PATCH /loans/{id}`). Remaining principal balances and daily interest costs update dynamically based on recorded amortization events.
