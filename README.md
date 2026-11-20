# Mend — The Anxiety-Free Household & Family Financial Platform

Mend is an anxiety-free household financial platform built with **Next.js (App Router)** and **FastAPI (Python)**, backed by **PostgreSQL / SQLAlchemy Async** and **Argon2id** security.

---

## 🌟 Core Principles

1. **Anxiety-Free Financial Ritual**: A calm 30-second evening check-in (`/daily-logs`) that builds mindful spending awareness without guilt, shame, or complex budgeting rules.
2. **Tomorrow's Radar**: Proactively surfaces upcoming utility and household bills (`/bills/radar`) 24 to 48 hours before they become due, eliminating late fees and cutoff notices.
3. **Strict Dual-Account Privacy Boundary**: Complete mathematical and structural isolation between personal spaces and household hubs. Personal loans and liabilities are **100% private** and can never leak to family members.
4. **Financial Precision**: Zero floating-point arithmetic. All monetary values are handled as fixed-point `Numeric(14, 2)` in PostgreSQL, Python `Decimal`, and strings end-to-end in TypeScript.
5. **Robust Payment Integrity**: Multi-layered concurrency controls, partial unique indexes, client-scoped idempotency keys, payment cancellation, webhook signature verification, and event ledger deduplication.
6. **Peaceful Check-in Reminders**: Twice-daily in-app reminders (10:00 morning & 18:00 evening) calculated in each user's own timezone via `zoneinfo`, with evening auto-suppression if today's check-in was already logged, idempotent database deduplication, and zero debt/amount shame in notification copy.

---

## 🏗️ Architecture & Single Source of Truth

```
┌────────────────────────────────────────────────────────┐
│                   Next.js App Router                   │
│           (Reverse Proxies /api/v1/* to FastAPI)       │
└──────────────────────────┬─────────────────────────────┘
                           │ Single-Origin HTTP / Cookie
┌──────────────────────────▼─────────────────────────────┐
│                     FastAPI Core                       │
│                   (/api/v1 Endpoints)                  │
│   • Argon2id Authentication & Token Rotation           │
│   • Decimal Financial Math & Dynamic Amortization      │
│   • Strict Dual-Account Privacy Enforcement            │
│   • Idempotent Payments, Webhooks & Outbox Worker      │
└──────────────────────────┬─────────────────────────────┘
                           │ SQLAlchemy 2.0 Async
┌──────────────────────────▼─────────────────────────────┐
│                 PostgreSQL Database                    │
│   • Numeric(14, 2) Monetary Columns                    │
│   • Row-Level Locks & Partial Unique Indexes           │
│   • Alembic Schema Versioning & Migrations             │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Minimal production dependencies:
pip install -r requirements.txt
# Testing and development dependencies (pytest, httpx, etc.):
pip install -r requirements-dev.txt

# Run migrations (forward-only, baseline migrations immutable):
python -m alembic -c backend/alembic.ini upgrade head

uvicorn app.main:app --reload --port 8000
```

### Migration Rule
* **Forward-Only & Immutable**: Never edit an applied Alembic migration file in-place. Any schema evolution (tables, columns, indexes, constraints) must be authored as a new, forward-only revision:
  ```bash
  python -m alembic -c backend/alembic.ini revision -m "add_feature_column"
  ```
* **Zero Schema Drift**: Always verify there is no drift between SQLAlchemy models and database migrations:
  ```bash
  python -m alembic -c backend/alembic.ini check
  ```

---

### Local PostgreSQL Setup & Verification (Without Docker)

You can run and test against a real PostgreSQL instance locally without Docker:

#### 1. Starting PostgreSQL
* **Windows (portable binaries or installed service):**
  ```powershell
  # Using pg_ctl with a local data cluster (e.g., C:\Users\gowth\pgsql\data):
  pg_ctl -D C:\Users\gowth\pgsql\data -l C:\Users\gowth\pgsql\logfile.log start

  # Or if installed as a Windows service:
  net start postgresql-x64-16
  ```
* **Linux / macOS:**
  ```bash
  # Linux systemd:
  sudo systemctl start postgresql
  # macOS Homebrew:
  brew services start postgresql@16
  ```

#### 2. Running the Automated PostgreSQL Verification Script
The repository provides `scripts/verify_postgres.py` to automate end-to-end PostgreSQL validation:
1. Drops and recreates an isolated empty test database (`mend_empty_test`).
2. Runs `alembic upgrade head` from baseline to verify transactional DDL.
3. Runs `alembic check` ensuring zero model-to-database schema drift.
4. Executes the full 34-test pytest suite with `TEST_DATABASE_URL` pointing to PostgreSQL (including the row-level `FOR UPDATE` concurrency race condition test).

```bash
# Default connection is postgresql+asyncpg://postgres@127.0.0.1:5432/mend_test
python scripts/verify_postgres.py

# Or supply custom credentials:
TEST_DATABASE_URL="postgresql+asyncpg://user:pass@127.0.0.1:5432/mend_test" python scripts/verify_postgres.py
```

### 2. Frontend (Next.js)
```bash
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Verification & Test Suite

All changes are strictly verified across backend, frontend, static AST checks, and Playwright end-to-end browser journeys:
```bash
# 1. Backend Pytest Suite (Auth, Privacy Matrix, Payments, Webhook Ledger, Loans, Migrations)
python -m pytest -q

# 2. Frontend TypeScript Typecheck
npx tsc --noEmit

# 3. Frontend ESLint
npm run lint

# 4. Next.js Production Build
npm run build

# 5. Frontend Static Integrity Checks (Asserts zero parseFloat, strict CSP, required models)
npm run test:static

# 6. Real Playwright End-to-End User Journey (Register -> Verify Email -> Banner Dismissal -> Add Bill -> Pay via UPI -> Paid Attribution -> Logout)
npm run test:e2e

# 7. PostgreSQL End-to-End Suite & Concurrency Proof
python scripts/verify_postgres.py

# 8. Docker Compose Config & Verification (Requires Docker engine installed)
docker compose config
docker compose up --build
```

---

## 🔐 Email & Phone Verification and Payment Gating

Mend provides end-to-end verification workflows:
- **Endpoints**: `/api/v1/verification/email/send`, `/api/v1/verification/email/confirm`, `/api/v1/verification/phone/send`, `/api/v1/verification/phone/confirm`.
- **E.164 Normalization**: Bare 10-digit Indian numbers default to `+91`; whitespace and hyphens are stripped.
- **Enumeration Safety**: Sends unconditionally return 202 Accepted. Uniqueness for verified phone numbers is enforced via partial unique index (`uq_verified_phone_e164`).
- **Cryptographic Security**: 6-digit random codes from `secrets`, 10-minute TTL, constant-time comparison, 5 wrong attempts locks challenge.
- **Rate Limits & Cooldowns**: 60s cooldown, max 5 sends/hour per user+channel tracked in DB, plus in-memory IP rate limiting.
- **Outbox Encryption**: Sensitive verification dispatch payloads are encrypted with AES-256-GCM and wiped to `{}` immediately upon delivery.
- **Payment Gating**: `REQUIRE_EMAIL_VERIFICATION_FOR_PAYMENTS=true` and `REQUIRE_PHONE_VERIFICATION_FOR_PAYMENTS=false`. Payments and mark-paid return 403 `EMAIL_NOT_VERIFIED` / `PHONE_NOT_VERIFIED` if unverified.
- **Production Guard**: Startup fail-fast prevents running with `EMAIL_PROVIDER="console"` or `SMS_PROVIDER="console"` in production. Test helper endpoint returns 404 in production.

---

## ⏰ Daily Check-in Reminders (Round 8)

Mend provides peaceful, non-intrusive in-app reminders to anchor daily mindfulness without financial dread:
- **Morning Slot (10:00)**: `"Plan your day: check Tomorrow's Radar and list what is due."`
- **Evening Slot (18:00)**: `"Time for your 30-second check-in: log today's spending."`
- **User Timezone Computation**: Local time is computed using standard IANA timezones via Python `zoneinfo.ZoneInfo`, correctly handling Daylight Saving Time (DST) transitions with an automatic fallback to `Asia/Kolkata` for unrecognized strings.
- **Idempotency & Deduplication**: Managed via composite unique constraint `uq_notifications_user_dedupe` on `(user_id, dedupe_key)` (`reminder:morning:YYYY-MM-DD` and `reminder:evening:YYYY-MM-DD`). Scheduler restarts or concurrent worker runs will never create duplicate notifications.
- **Evening Auto-Skip**: The 18:00 evening check-in reminder is automatically skipped if the user has already submitted today's daily log (entries or notes).
- **User Preference Controls**: Per-user flags `reminder_morning_enabled` and `reminder_evening_enabled` (defaulting to `true`) can be inspected and updated via `PATCH /api/v1/me` and `PATCH /api/v1/me/reminders`.
- **Frontend Integration**: Active reminders appear as a calm `ReminderBanner` with 1-click action buttons ("Review Radar", "Check In Now") and dismiss controls, accompanied by a `ReminderSettingsModal` accessible from the top navigation bar.
- **Privacy & Money Integrity**: Reminder copy strictly contains **zero** amounts, zero currency symbols, and zero loan/debt/liability information.

---

## ⚠️ Known Limits & Verification Status

- **PostgreSQL**: Verified locally against Windows PostgreSQL 16 on port 5432 with `asyncpg` (`TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:5432/mend_test`), passing all 59 tests including `test_postgres_concurrent_payment_race_condition`, `test_concurrent_confirm_race_condition`, and clean Alembic upgrade from scratch (`0fa0163424e7` -> `a2551f055745` -> `fccb551da8cb`).
- **Live SMTP / SMS Gateways**: **NOT RUN** in automated CI/test suites because live third-party credentials (Gmail App Password, Twilio SID/token, MSG91 DLT) and external network egress are disabled in the test sandbox. Verified via `ConsoleEmailSender`, `ConsoleSmsSender`, `SmtpEmailSender` unit tests (verifying TLS enforcement, timeout, and plaintext rejection), and outbox publisher delivery with payload clearance and retry. A manual verification smoke test script is provided at `python scripts/smtp_smoke.py <recipient>`.
- **Docker / Docker Compose**: **NOT RUN** locally because Docker Engine is not installed on this host environment. Dockerfile and `docker-compose.yml` are maintained and configured with unprivileged users (`menduser`), parameterized database credentials, and minimal production dependencies (`requirements.txt`).
- **Rate Limiting**: Sliding-window rate limiter is currently in-process and per-worker memory with an LRU cap of 10,000 keys. Multi-worker deployments require Redis.
- **Payment Gateway**: Payments are currently driven by a simulated sandbox provider (`ENABLE_SANDBOX_PAYMENTS=True`). No live NPCI UPI or BBPS endpoints are connected.
- **Self-Reported Payments**: Marked as `PAID_UNVERIFIED` until external biller confirmation.

---

## 🔒 Security Policies
Refer to [SECURITY.md](SECURITY.md) for full details on authentication hardening, token rotation grace windows, row-level locks, CSRF origin verification, and data isolation guarantees.
