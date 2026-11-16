# FamilyVault (Kavach) — "Once a Day, Keep the Stress Away"

An anxiety-free household financial and liability management web application built with **Next.js**, **Tailwind CSS**, **Node.js / Express**, and **PostgreSQL with Prisma ORM**.

Unlike traditional finance applications that induce anxiety with aggressive red alerts and tedious receipt-entry fatigue, **FamilyVault** centers around a calm 30-second evening check-in ritual, proactive tomorrow radar, and an anxiety-shielded loan vault.

---

## 🌟 Core UX Principles

1. **"Once a Day, Keep the Stress Away"**: No real-time data entry fatigue. A quick 30-second evening check-in with category quick-chips.
2. **Proactive over Reactive**: "Tomorrow’s Radar" surfaces upcoming bills 24 hours in advance to eliminate late fees and unexpected shocks.
3. **Anxiety Shielding**: Heavy debt analytics and amortization tables are hidden by default inside the **Liabilities Vault** behind an intentional click.

---

## 🏗️ Architecture & Tech Stack

- **Frontend**: Next.js 16 (React 19) + Tailwind CSS + Lucide Icons + Canvas Confetti.
- **Backend API**:
  - **Native Next.js API Routes** (`/api/...`) for zero-configuration, unified full-stack execution.
  - **Standalone Express.js Server** (`server/index.js`) for dedicated Node.js API deployments.
- **Database & ORM**: PostgreSQL with Prisma ORM (`prisma/schema.prisma` & `prisma.config.ts`).
- **Financial Calculation Engine**: Mathematically rigorous amortization model (`src/lib/amortization.ts`) with multi-granular Daily, Monthly, and Yearly perspectives.

---

## 🗄️ Database Schema (`prisma/schema.prisma`)

```prisma
datasource db {
  provider = "postgresql"
}

generator client {
  provider = "prisma-client-js"
}

enum RecurringType {
  NONE
  MONTHLY
  YEARLY
}

model User {
  id               String             @id @default(uuid())
  email            String             @unique
  passwordHash     String
  createdAt        DateTime           @default(now())
  dailyLogs        DailyLog[]
  upcomingRadars   UpcomingRadar[]
  liabilities      LiabilitiesVault[]

  @@map("users")
}

model DailyLog {
  id                  String   @id @default(uuid())
  userId              String
  user                User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  logDate             DateTime @default(now())
  totalSpent          Float
  categoriesBreakdown Json     // e.g. { "groceries": 450, "bills": 1200, "transport": 150, "misc": 0 }
  notes               String?
  createdAt           DateTime @default(now())

  @@index([userId, logDate])
  @@map("daily_logs")
}

model UpcomingRadar {
  id            String        @id @default(uuid())
  userId        String
  user          User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  title         String        // e.g., "Wi-Fi Bill", "Car EMI"
  amount        Float
  dueDate       DateTime
  isPaid        Boolean       @default(false)
  recurringType RecurringType @default(NONE)
  createdAt     DateTime      @default(now())

  @@index([userId, dueDate])
  @@map("upcoming_radars")
}

model LiabilitiesVault {
  id              String   @id @default(uuid())
  userId          String
  user            User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  loanName        String   // e.g., "Home Loan - SBI", "Car Loan"
  principalAmount Float
  interestRate    Float    // Annual percentage e.g. 8.5
  tenureMonths    Int
  startDate       DateTime
  monthlyEMI      Float
  createdAt       DateTime @default(now())

  @@index([userId])
  @@map("liabilities_vault")
}
```

---

## 🧮 Mathematical Formulas & Financial Engine

### 1. Daily Cost of Debt Formula
$$\text{Daily Interest Cost} = \frac{\text{Remaining Principal} \times \text{Annual Interest Rate}}{365 \times 100}$$

*Psychological Framing*: Shows interest as a small daily rental cost (e.g., ₹990/day $\approx$ 6 artisan coffees) rather than a scary multi-lakh balance, reassuring users that debt is simply rented capital.

### 2. Standard Monthly EMI Formula
$$\text{EMI} = \frac{P \times R \times (1 + R)^N}{(1 + R)^N - 1}$$
Where:
- $P$ = Principal amount
- $R = \frac{\text{Annual Interest Rate}}{12 \times 100}$ (Monthly interest rate)
- $N$ = Tenure in months

### 3. Prepayment Compound Simulator
Calculates the exact impact of lump-sum prepayments:
- Reduced tenure: $\Delta N = N_{\text{original}} - N_{\text{new}}$ (Months and years shaved)
- Total interest saved: $\sum I_{\text{original}} - \sum I_{\text{with prepayment}}$

### 4. Indian Income Tax Exemption Estimates
- **Section 24(b)**: Home loan interest deduction up to **₹2,00,000/year**.
- **Section 80C**: Principal repayment deduction up to **₹1,50,000/year**.
- **Total Combined Tax Shield**: Up to **₹3,50,000/year** ($\sim$₹1,05,000 saved at 30% tax slab).

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Generate Prisma Client
```bash
npm run prisma:generate
```

### 3. Run Development Server (Next.js full-stack)
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the application.

### 4. Optional: Run Standalone Express API Server
```bash
npm run server:express
```
Runs on `http://localhost:4000` with the matching REST API endpoints.

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Streak counter, today's status, tomorrow's bills, and vault summary |
| `GET` | `/api/daily-logs` | Retrieve daily check-in history & active streak |
| `POST` | `/api/daily-logs` | Submit 30-second nightly check-in with category quick-chips |
| `GET` | `/api/radar/tomorrow` | Filter bills hitting tomorrow |
| `GET` | `/api/radar` | Get all upcoming bills |
| `POST` | `/api/radar` | Add new proactive bill / reminder |
| `PATCH` | `/api/radar/:id` | Toggle bill paid / unpaid |
| `GET` | `/api/liabilities` | List all active loans with daily cost metrics |
| `POST` | `/api/liabilities` | Add new loan to vault |
| `GET` | `/api/liabilities/:id/amortization` | Full daily, monthly, yearly amortization with prepayment simulation |
