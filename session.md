# Mend — Session & Project Log

> **Application Name**: Mend  
> **Core Philosophy**: Anxiety-Free Household & Family Financial Platform  
> **Repository Root**: `c:\Users\gowth\OneDrive\Desktop\mend`  
> **Current Version**: 0.2.0 (Enhanced Master Architecture)  
> **Last Updated**: 2026-11-15T23:15:00+05:30  

---

## 1. Project Overview & Vision

**Mend** is designed from the ground up to eliminate the dread, cognitive overload, and domestic friction of household finance:
- **"Once a day, keep the stress away"**: No manual receipt typing or itemized bookkeeping fatigue. A simple 30-second evening check-in ritual using quick category chips.
- **Proactive over Reactive**: "Tomorrow's Radar" ensures bills and subscriptions are visible before due dates, avoiding late fees.
- **Strict Data Isolation**: Personal liabilities (loans, mortgages, vehicle loans), daily logs, and personal bills are strictly sandboxed in private individual spaces. Family endpoints exclusively serve shared utilities and subscriptions—zero personal liabilities ever leak to family members. Outsiders receive `404 Not Found` (never 403) so group existence is never leaked.
- **Financial Precision**: Floats are strictly prohibited for money. Database: `Numeric(14,2)`. Python: `Decimal`. JSON: money as strings (`"1499.00"`). TypeScript: strings formatted for display only.
- **Backend Authority**: The UI hides controls for comfort, but every rule is enforced on the server. Routers call services, services call repositories, repositories always take the acting user/group context and filter by it.
- **1-Tap Frictionless Settlement**: Standard NPCI UPI Intent deep linking (`upi://pay?pa=...`) for instant settlement via Google Pay, PhonePe, Paytm, or BHIM, with automatic reconciliation (`✓ Paid by [Name] via UPI`) and strike-through to `₹0 Due`.
- **Auto-Discovery via Phone & Email**: RBI Account Aggregator & NPCI BBPS mock discovery linking active household bills and personal loans with a 4-digit OTP.

---

## 2. Tech Stack & Infrastructure

- **Backend**: Python 3.14 / 3.12, FastAPI under `/api/v1`, Pydantic v2, SQLAlchemy 2.0 (`Mapped[]` typed style), Alembic, Pytest, APScheduler.
- **Frontend**: Next.js 16 (App Router, Turbopack, React 19, TypeScript, Tailwind CSS v4 mobile-first).
- **Database**: PostgreSQL 16 (production/Docker) & SQLite aiosqlite (isolated testing).
- **Payment & Bill Providers**: `PaymentProvider` (`SandboxUPIProvider`) and `BillFetchProvider` (`MockBBPSProvider`).
- **Containers & CI**: Docker, `docker-compose.yml` (`api`, `web`, `db`), and GitHub Actions CI workflow (`.github/workflows/ci.yml`).

---

## 3. Database Schema (SQLAlchemy 2.0 Models)

| Model | Purpose | Privacy & Constraints |
| :--- | :--- | :--- |
| `User` | User profile, Argon2id password hash, timezone | Core System |
| `RefreshToken` | Rotation chain with reuse breach detection | Core System |
| `FamilyGroup` | Household unit (e.g., "The Ejjurothu Family") | Shared Family |
| `FamilyMember` | Membership table (`ADMIN` / `MEMBER`) | Unique `(user_id, family_group_id)` |
| `FamilyInvitation` | Secure 32-byte token (stored as SHA-256 hash), single use | Expiry (7 days), one pending per (group, email) |
| `ExpenseCategory` | Seed defaults + custom user categories | System default (`user_id IS NULL`) or owner |
| `DailyLog` | The 30-second nightly check-in logs | Unique `(user_id, log_date)`, computed total |
| `DailyLogEntry` | Itemized category amount check `amount > 0` | Linked to owner's log and owner/system category |
| `UpcomingRadar` | Proactive bill engine | XOR constraint: `user_id` XOR `family_group_id` |
| `BillReminder` | Offset triggers (3, 1, 0 days) | Unique `(bill_id, offset_days)` |
| `PaymentTransaction` | Two-transaction settlement with provider intent | Status `PENDING`, `SUCCESS`, `FAILED` |
| `PaymentEvent` | Append-only audit trail for payments | Blocked from updates/deletions once finalized |
| `LiabilitiesVault` | Personal loans, mortgages, EMI schedules, interest rates | **Strictly 100% Private Individual**, zero family FK |
| `LoanPayment` | Principal & interest breakdown per installment | Private Individual |
| `LoanPrepayment` | Lump-sum prepayments (`REDUCE_TENURE` / `REDUCE_EMI`) | Private Individual |
| `Notification` | In-app notification center | User-only, **never contains loan data** |
| `AuditLog` | Append-only system audit log | Sensitive data (passwords, tokens, loans) redacted |
| `OutboxEvent` | Transactional outbox for event publishing | Polled with `SELECT FOR UPDATE SKIP LOCKED` |

---

## 4. API Surface (`/api/v1`)

### **Authentication & Profile**
- `POST /api/v1/auth/register`: Argon2id registration.
- `POST /api/v1/auth/login`: Returns access JWT (15 mins) and sets httpOnly refresh cookie (30 days).
- `POST /api/v1/auth/refresh`: Rotates refresh token; reuse of revoked token revokes whole chain.
- `POST /api/v1/auth/logout`: Revokes refresh token.
- `GET /api/v1/me`: Returns acting user profile.
- `PATCH /api/v1/me`: Updates display name or timezone.

### **Family Management & Membership**
- `POST /api/v1/families`: Creates family group (creator becomes Admin).
- `GET /api/v1/families`: Lists all groups the acting user belongs to.
- `GET /api/v1/families/{id}`: Detailed group overview (404 for outsiders).
- `PATCH /api/v1/families/{id}`: Updates group name/timezone (Admin only: 403 for members, 404 for outsiders).
- `GET /api/v1/families/{id}/members`: Lists members with roles.
- `POST /api/v1/families/{id}/invitations`: Issues single-use invite link (Admin only).
- `GET /api/v1/families/{id}/invitations`: Lists pending invitations (Admin only).
- `DELETE /api/v1/families/{id}/invitations/{inv_id}`: Revokes invitation (Admin only).
- `POST /api/v1/invitations/accept`: Accepts invitation using single-use raw token.
- `PATCH /api/v1/families/{id}/members/{uid}`: Promotes/demotes member role (Guarded: cannot demote last admin -> 409).
- `DELETE /api/v1/families/{id}/members/{uid}`: Removes member (Guarded: cannot remove last admin -> 409).
- `POST /api/v1/families/{id}/leave`: Leaves group (Guarded: last admin cannot leave without promoting someone -> 409).

### **Family Bills & Payments**
- `GET /api/v1/families/{id}/bills`: Views family bills (All members).
- `POST /api/v1/families/{id}/bills`: Adds shared bill (Admin only: 403 for members).
- `GET /api/v1/families/{id}/bills/{bid}`: Detailed bill view with unmasked consumer number.
- `PATCH /api/v1/families/{id}/bills/{bid}`: Edits shared bill (Admin only).
- `DELETE /api/v1/families/{id}/bills/{bid}`: Soft-deletes shared bill (Admin only).
- `POST /api/v1/families/{id}/bills/{bid}/pay`: 1-tap UPI payment with `Idempotency-Key` (All members).
- `GET /api/v1/families/{id}/payments`: Read-only group payment history with attribution.
- `POST /api/v1/families/{id}/bills/fetch-bbps`: Simulates BBPS auto-fetch (Admin only).

### **Personal Bills**
- `GET /api/v1/bills`: Lists personal bills (Owner only).
- `POST /api/v1/bills`: Creates personal bill.
- `GET /api/v1/bills/{id}`: Detailed view (Owner only: 404 for others).
- `PATCH /api/v1/bills/{id}`: Updates bill.
- `DELETE /api/v1/bills/{id}`: Soft-deletes bill.
- `POST /api/v1/bills/{id}/pay`: Pays personal bill with `Idempotency-Key`.

### **Daily Expense Check-in**
- `GET /api/v1/categories`: Lists system defaults + user custom categories.
- `POST /api/v1/categories`: Creates user-specific category chip.
- `GET /api/v1/daily-logs?date=YYYY-MM-DD`: Returns day's check-in with dynamically computed `total_spent`.
- `PUT /api/v1/daily-logs/{date}/notes`: Updates reflection notes.
- `POST /api/v1/daily-logs/{date}/entries`: Adds category entry with Decimal precision.
- `DELETE /api/v1/daily-logs/{date}/entries/{entry_id}`: Removes entry.

### **Liabilities Vault (100% Private)**
- `GET /api/v1/loans`: Lists user's private loans (Zero family visibility).
- `POST /api/v1/loans`: Adds loan to vault.
- `GET /api/v1/loans/{id}`: Loan details.
- `GET /api/v1/loans/{id}/daily-cost`: Calculates daily interest cost: `(balance * rate) / (365 * 100)`.
- `GET /api/v1/loans/{id}/amortization`: Complete schedule; final installment clears balance to 0.00 exactly.
- `POST /api/v1/loans/{id}/simulate-prepayment`: Simulates lump-sum additions (`REDUCE_TENURE` vs `REDUCE_EMI`).
- `DELETE /api/v1/loans/{id}`: Removes loan from vault.

### **Notifications**
- `GET /api/v1/notifications`: Lists in-app notifications (Never contains loan info).
- `PATCH /api/v1/notifications/{id}/read`: Marks notification read.
- `POST /api/v1/notifications/read-all`: Marks all read.

---

## 5. Chronological Session Log

### **Session 1 — 2026-11-15**
- Initial Next.js mobile web application prototype with Prisma ORM, mobile bottom sheets, 1-tap UPI deep link simulation, and dual-account mode toggle.
- Verified in mobile browser viewport (390x844).

### **Session 2 — 2026-11-15 (Enhanced Master Architecture)**
- **Objective**: Full implementation of the Enhanced Master Specification for Mend:
  1. Built production-grade Python 3.12+ FastAPI backend under `/api/v1` with Pydantic v2 schemas.
  2. Implemented SQLAlchemy 2.0 models with typed `Mapped[]` style across 18 relational tables.
  3. Enforced strict financial precision: zero floats allowed on monetary inputs, strict Decimal arithmetic, and string serialization.
  4. Built complete repository layer enforcing mandatory owner/group filters on every query.
  5. Implemented Section 3.2 Permission Matrix with automated status assertions (Owner, Admin, Member, Outsider -> 404 Not Found).
  6. Implemented Admin Lifecycle Guards preventing the last admin from leaving or being demoted (409 Conflict).
  7. Built short-transaction locking payment engine with NPCI UPI Intent generation, idempotency key guarantees, and transactional outbox.
  8. Implemented high-precision Decimal loan amortization, daily cost of debt calculation, and prepayment simulator.
  9. Implemented background jobs via APScheduler: stale pending payment reconciliation and transactional outbox publisher.
  10. Added `docker-compose.yml` (`api`, `web`, `db`) and `.github/workflows/ci.yml`.
  11. Executed Pytest test suite: **7 passed in 0.89s (100% green)**.

### **Session 3 — 2026-11-16**
- **User Preference**: Communication style set to simple, clear, easy-to-read English without heavy technical jargon.
- **UI/UX Refinement**:
  - Simplified copy across `DashboardView` and modals (clear, natural language, friendly terms, zero banking jargon).
  - Converted "Past 7 Days Consistency" from horizontal chips into a sleek vertical bar chart with proportional heights, daily amounts, day labels, and active green dots.
- **Comprehensive Walkthrough**: Documented full screen-by-screen, feature-by-feature explanation of how the mobile application works.
- **Interactive Live Demo**:
  - Ran automated mobile browser demonstration on `http://localhost:3000` (viewport 390x844).
  - Walked through Family Shared Hub, 1-tap UPI payment reconciliation with strike-through to ₹0 Due, 30s check-in with confetti, and the Private Liabilities Vault.
  - Demo screenshot artifacts: `final_step_24.png`, `final_step_6.png`.

### **Session 4 — 2026-11-16 (Safety Verification & External App Auto-Sync)**
- **User Safety Concern**:
  - Prevent accidental manual clicks on "Mark Paid" without paying, which could mislead the family into thinking electricity/broadband is settled when it wasn't.
  - Automatically detect and update bills if they are paid in another app (PhonePe, Google Pay, Paytm, or NetBanking).
- **Engineering & UI Solutions Implemented**:
  1. **Vertical Consistency Bar Chart**:
     - Upgraded the 7-day expense check-in view into a dynamic vertical bar chart with proportional fill heights, day badges, and active streak dots.
  2. **Safe Payment Verification Sheet (`SafeVerifyPaymentModal.tsx`)**:
     - Intercepts all "Mark Paid" clicks with an explanation modal: *"Prevent missed bills and unexpected service cutoffs"*.
     - App Selector: Lets user select where they paid (Google Pay, PhonePe, Paytm, NetBanking).
     - **Option A — Verify with Biller (Auto-Check BBPS)**: Queries provider status directly; on confirmation marks `✓ Verified with Biller (BBPS)`.
     - **Option B — Self-Reported with Warning Flag**: If marked without biller verification, flags with amber badge `⚠️ Self-Reported: Paid by [Name] ([App]) • Checking with biller...` to prevent false domestic assumptions.
  3. **External Payment Auto-Sync Engine**:
     - Integrated `/api/radar/auto-sync` with `dataStore.ts` to poll BBPS registry and auto-clear bills paid outside Mend with verified provenance.
  4. **Browser Verification**:
     - Verified live on `http://localhost:3000` in mobile viewport.
     - Captured evidence: `final_step_6.png` (bar chart), `step_41_shot_1_verification_sheet.png` (safety check bottom sheet), and `final_step_43.png` (settled state with verified badges).

### **Session 5 — 2026-11-16 (Streak Removal & Multi-Tenant Dual User Isolation)**
- **User Requests**:
  1. "Remove the unwanted detail and mentioning / we do not need the streak alive thing" — Strip out gamified streak pressure, fire/flame icons, and "Streak Alive" badges in adherence to the core Mend philosophy: *"Never shames, never shows streaks as guilt"*.
  2. "Gowtham and Priya are two different users right why they are having the same data even after the switch" — Fix the shared mock data problem so Gowtham and Priya have completely distinct personal spaces, check-in histories, personal bills, and private loans.
- **Changes Implemented**:
  1. **Streak & Gamification Clutter Removed**:
     - Removed `{streak}d` flame icon badge from `MobileHeader.tsx`.
     - Removed `{streak} Days` and flame icon from `DashboardView.tsx` hero area, replaced with peaceful date display.
     - Removed `Streak Alive 🔥` badge and bottom indicator dots from the 7-day spending vertical bar chart.
  2. **Complete Data Isolation between Gowtham & Priya**:
     - **Gowtham's Personal Space**:
       - Daily spending logs: ₹350 groceries, ₹80 transport, ₹250 dining, etc.
       - Private Liabilities: SBI Home Loan (₹45L) + HDFC Vehicle Loan (₹6.5L) = ₹1,141 daily debt cost.
       - Personal bill in Radar: HDFC Car EMI Autopay.
     - **Priya's Personal Space**:
       - Daily spending logs: Distinct expense categories (₹180 groceries, ₹220 wellness/health, ₹340 dining).
       - Private Liabilities: ICICI Higher Education Loan (₹12L MBA loan) = ₹236 daily debt cost (1.6 coffees/day). 100% private from Gowtham.
       - Personal bill in Radar: Cult.fit Fitness Pass Autopay (₹1,499).
     - **Family Shared Hub**: Both see shared utilities (BESCOM electricity, Airtel broadband, maintenance), with clear attribution of who paid.
  3. **API & Route Updates**:
     - Parameterized `userId` across `/api/dashboard`, `/api/liabilities`, `/api/radar`, and `/api/daily-logs`.
     - Fixed dynamic amortization endpoint `/api/liabilities/[id]/amortization` to work for all loan IDs.
  4. **Browser & Mobile Viewport Verification**:
     - Subagent verified clean user switching on `http://localhost:3000` (viewport 390x844).
     - Screenshots captured: `step_36_shot_1.png` (Gowtham clean header), `step_55_shot_1_priya_dashboard_top.png` (Priya dashboard), `step_57_shot_1_priya_vault_screen.png` (Priya sandboxed education loan), and `final_step_65.png`.

### **Session 6 — 2026-11-16 (Master Blueprint Reconciled: Precision, Models, & Architecture)**
- **User Review Items Addressed**:
  1. **Contradictions Reconciled**:
     - Clarified that UPI deep links are simulated client-side intents; settlement requires asynchronous gateway webhooks or BBPS clearance polling.
     - Formally labeled Auto-Sync, Auto-Discover, BBPS, and Account Aggregator as mock-only for v1, with the 4921 OTP gated behind sandbox flags.
     - Added `PAID_UNVERIFIED` to the data model with a clear 72h SLA lifecycle, automated clearance, dispute triggers, and admin fallback.
     - Explicitly documented the two backends: Next.js `/api/*` + `dataStore.ts` as an interactive UI mock harness, and Python FastAPI (`/api/v1`) as authoritative production. Noted that the client-side user toggle does not prove server isolation.
     - Enforced anti-gamification: removed confetti bursts and "Daily Win" labels (now "Save Daily Check-In"), and replaced the "coffee scale" with annualized interest to avoid debt shame.
  2. **Accuracy Issues Resolved**:
     - Restored `ExpenseCategory` to the model inventory, bringing the table count to exactly 18 models.
     - Added missing model columns: `FamilyGroup.timezone`, `PaymentTransaction.idempotency_key`, `PaymentTransaction.provider_intent_id`, `FamilyInvitation.expires_at`, and `UpcomingRadar.last_reconciled_at`.
     - Fully populated Section 6 with end-to-end execution flow diagrams and sequence specifications.
     - Corrected interest math: noted that ₹43L at 8.5% is about ₹1,001/day (₹1,004/day on ₹43.12L amortized balance).
     - Corrected tax shield rules: explicitly noted that Section 24(b) applies to self-occupied property, deductions apply under Old Tax Regime only, 80C is shared, and ₹1.05L excludes 4% cess. Versioned as `IN_OLD_REGIME_FY24_25`.
     - Documented IEEE 754 precision constraints for client-side JavaScript math vs Python `Decimal`.
  3. **Architectural Gaps Documented**:
     - Double-payment prevention via partial unique index `uq_bill_active_payment`.
     - Idempotency key scoping and 409 Conflict handling for parameter mismatches.
     - HMAC-SHA256 webhook signatures, 5-minute replay window, and processed event deduplication.
     - Soft-delete semantics preserving payment ledger integrity.
     - Out-of-band link generation for invitation delivery.
     - GDPR/DPDP data export, account deletion PII scrubbing, and zero-PII logging rules.
     - Clarified single-row XOR ownership for shared utilities (BESCOM/Netflix).
     - Sanitized all personal details, local filesystem paths, emails, and phone numbers.
- **System Status**:
  - Live dev server running on `http://localhost:3000`.
  - Backend Pytest test suite: 7/7 passed in 1.53s (100% green).
  - Master blueprint updated at `mend_complete_system_blueprint.md`.
  - Initial repository pushed to `https://github.com/gowthame23/medu` with `gowthame23` as sole contributor.


### **Session 7 — 2026-11-16 (FastAPI Consolidation, Full Security Hardening & Verified Commit)**
- **User Directives Addressed**:
  1. **Consolidation on Single Authoritative Backend**:
     - Deleted legacy Next.js mock API routes (`src/app/api/*`), in-memory store (`src/lib/dataStore.ts`), duplicate Express server (`server/index.js`), and unused Prisma schema (`prisma/`).
     - Established FastAPI core (`/api/v1`) as the single source of truth for all business logic, financial math, and authentication.
     - Created typed API client `src/lib/api.ts` with in-memory access tokens (never stored in localStorage) and silent refresh on mount.
     - Rewired Next.js `rewrites()` in `next.config.ts` to proxy `/api/v1/*` to the FastAPI backend, preserving a single-origin perimeter.
     - Added real authentication UI (`/login` and `/register`) and application `AuthContext`.
  2. **Security & Cryptographic Hardening**:
     - Implemented 30-second concurrency grace window on refresh token rotation to accommodate React StrictMode without session revocation.
     - Guarded `WEBHOOK_SECRET` and `SECRET_KEY` with production validators: refuses startup if default dev values or keys < 32 chars are detected in production.
     - Added cryptographic amount check to webhook handler: payload `amount` must match `txn.amount` exactly or raises HTTP 400.
     - Upgraded payment event deduplication from a JSON scan to an indexed `UNIQUE(event_id)` database column in `payment_events` with `SELECT ... FOR UPDATE` row locking.
     - Eliminated account enumeration and real UUID/age leakage in registration: returns uniform HTTP 201 with synthetic pseudo-random UUIDs and fresh current timestamps.
     - Hardened sliding-window rate limiters: only trusts `X-Forwarded-For` from configured `TRUSTED_PROXIES` (`127.0.0.1`, `::1`), bounds in-memory storage to 10,000 keys with LRU/FIFO eviction, and added protection to `/auth/refresh` (30/min) and `/invitations/accept` (10/min).
     - Upgraded CSRF/Origin verification middleware: mutating requests without an `Origin` or `Referer` header are rejected with `403 Forbidden` in production, and localhost/testserver exemptions are strictly disabled in production.
     - Removed `'unsafe-eval'` and `'unsafe-inline'` from production Next.js Content Security Policy (CSP), gating dev exemptions behind `isDev`. Calibrated HSTS to `max-age=31536000; includeSubDomains`.
     - Parameterized `docker-compose.yml` to require environment variables without insecure production fallbacks, supported by `.env.example`.
  3. **Payment Integrity & Liabilities Engine**:
     - Wrapped `POST /bills/{id}/mark-paid` in `PaymentService.settle_self_reported_payment()` with `SELECT ... FOR UPDATE`, soft-delete verification, and auto-recurrence spawning.
     - Rejected `PAID_UNVERIFIED` bills on `/pay` and `/mark-paid` with `409 ALREADY_PAID`.
     - Added `POST /bills/{id}/payment/cancel` to release in-flight locks.
     - Added dynamic loan amortizations: `POST /loans/{id}/payments`, `POST /loans/{id}/prepayments` (`REDUCE_TENURE` vs `REDUCE_EMI`), and `PATCH /loans/{id}`.
     - Replaced all frontend `parseFloat` and `Math.random` with integer paise and `crypto.randomUUID()`.
     - Created `test_extended_privacy_matrix.py` proving zero data leakage across personal radar, daily check-in notes, loan vaults, and immediate family access revocation.
  4. **Quality Gates & Commit**:
     - Pytest suite: 19 passed, 0 warnings (clean SQLite async engine + Alembic migration test from head down).
     - TypeScript: exit code 0 (`tsc --noEmit`).
     - ESLint: exit code 0 (`eslint`).
     - Frontend smoke test: exit code 0 (`node scripts/smoke_test.mjs`).
     - Production build: exit code 0 (`next build` with Turbopack).
     - Created Git commit `acc99ba` on branch `consolidate-fastapi` under sole contributor identity `gowthame23 <gowthame23@users.noreply.github.com>`.

---

### **Session 8 — 2026-11-16 (Tracking Artifacts & Continuous Documentation Workflow)**
- **User Directives Addressed**:
  1. **Dynamic Overwrite Report (`report.md`)**:
     - Created `report.md` in repository root.
     - Configured workflow to completely overwrite `report.md` on every update, reflecting the latest test results, architecture state, security posture, and git commit details.
  2. **Active Task Tracker (`tasks.md`)**:
     - Created `tasks.md` in repository root.
     - Outlined all completed phases (1 through 6) and defined upcoming roadmap tasks: remote push to `https://github.com/gowthame23/medu`, GitHub Actions CI pipeline execution with PostgreSQL, PR creation, and production staging.
  3. **Append-Only Chronological Session Log (`session.md`)**:
     - Strictly preserved all historical content in `session.md` without deletions.
     - Appended comprehensive logs for Sessions 7 and 8 to maintain an unbroken audit trail for every user prompt.
