# Mend — The Anxiety-Free Household & Family Financial Platform

Mend is an anxiety-free household financial platform built with **Next.js (App Router)** and **FastAPI (Python)**, backed by **PostgreSQL / SQLAlchemy Async** and **Argon2id** security.

---

## 🌟 Core Principles

1. **Anxiety-Free Financial Ritual**: A calm 30-second evening check-in (`/daily-logs`) that builds mindful spending awareness without guilt, shame, or complex budgeting rules.
2. **Tomorrow's Radar**: Proactively surfaces upcoming utility and household bills (`/bills/radar`) 24 to 48 hours before they become due, eliminating late fees and cutoff notices.
3. **Strict Dual-Account Privacy Boundary**: Complete mathematical and structural isolation between personal spaces and household hubs. Personal loans and liabilities are **100% private** and can never leak to family members.
4. **Financial Precision**: Zero floating-point arithmetic. All monetary values are handled as fixed-point `Numeric(14, 2)` in PostgreSQL, Python `Decimal`, and strings end-to-end in TypeScript.
5. **Robust Payment Integrity**: Multi-layered concurrency controls, partial unique indexes, client-scoped idempotency keys, payment cancellation, webhook signature verification, and event ledger deduplication.

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

pip install -r requirements.txt
# For testing and development:
pip install -r requirements-dev.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000
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

# 6. Real Playwright End-to-End User Journey (Register -> Login -> Dashboard -> Add Bill -> Pay via UPI -> Paid Attribution -> Logout)
npm run test:e2e

# 7. Docker Compose Config & Verification (Requires Docker engine installed)
docker compose config
docker compose up --build
```

---

## ⚠️ Known Limits & Implementation Scope (v1)

- **Rate Limiting**: Sliding-window rate limiter is currently in-process and per-worker memory. Multi-worker deployments require Redis.
- **Payment Gateway**: Payments are currently driven by a simulated sandbox provider (`ENABLE_SANDBOX_PAYMENTS=True`). No live NPCI UPI or BBPS endpoints are connected.
- **Self-Reported Payments**: Marked as `PAID_UNVERIFIED` until external biller confirmation.
- **Account Recovery**: No email verification tokens or SMTP delivery; no password reset flow. Authentication uses direct Argon2id credentials.

---

## 🔒 Security Policies
Refer to [SECURITY.md](SECURITY.md) for full details on authentication hardening, token rotation grace windows, row-level locks, CSRF origin verification, and data isolation guarantees.
