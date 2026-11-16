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

All changes are strictly verified across backend and frontend:
```bash
# Backend pytest suite (Auth, Privacy Matrix, Payments, Loans, Migrations, Financial Precision)
python -m pytest -q

# Frontend typecheck
npx tsc --noEmit

# Frontend linter
npm run lint

# Production compilation
npm run build
```

---

## 🔒 Security Policies
Refer to [SECURITY.md](SECURITY.md) for full details on authentication hardening, token rotation grace windows, row-level locks, CSRF origin verification, and data isolation guarantees.
