// Express.js Backend Server for FamilyVault / Kavach
// Node.js + Express API with Amortization Math Engine & Prisma compatibility

const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.EXPRESS_PORT || 4000;

app.use(cors());
app.use(express.json());

// --- In-Memory Repository with Realistic Defaults ---
let dailyLogs = [];
let upcomingRadars = [];
let liabilities = [];

function initDefaults() {
  const now = new Date();
  
  // Seed 14-day check-in streak
  for (let i = 14; i >= 1; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateKey = d.toISOString().split('T')[0];
    const groceries = 350 + (i % 4) * 120;
    const transport = 80 + (i % 3) * 40;
    const dining = i % 2 === 0 ? 250 : 0;
    const misc = 50 + (i % 5) * 30;

    dailyLogs.push({
      id: `log-${dateKey}`,
      userId: 'user-kavach-01',
      logDate: dateKey,
      totalSpent: groceries + transport + dining + misc,
      categoriesBreakdown: { groceries, transport, dining: dining || undefined, misc },
      notes: i === 1 ? 'Calm day. Quick grocery run and train pass.' : null,
      createdAt: new Date(d.getTime() + 20 * 3600 * 1000).toISOString(),
    });
  }

  // Seed Tomorrow's Radar
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const inThreeDays = new Date();
  inThreeDays.setDate(inThreeDays.getDate() + 3);

  upcomingRadars = [
    {
      id: 'radar-wifi',
      userId: 'user-kavach-01',
      title: 'Airtel Fiber Broadband',
      amount: 1179,
      dueDate: tomorrow.toISOString(),
      isPaid: false,
      recurringType: 'MONTHLY',
      category: 'Utilities',
      createdAt: new Date().toISOString(),
    },
    {
      id: 'radar-electricity',
      userId: 'user-kavach-01',
      title: 'Electricity Bill (BESCOM)',
      amount: 2450,
      dueDate: tomorrow.toISOString(),
      isPaid: false,
      recurringType: 'MONTHLY',
      category: 'Utilities',
      createdAt: new Date().toISOString(),
    },
    {
      id: 'radar-maintenance',
      userId: 'user-kavach-01',
      title: 'Apartment Society Maintenance',
      amount: 4200,
      dueDate: inThreeDays.toISOString(),
      isPaid: false,
      recurringType: 'MONTHLY',
      category: 'Housing',
      createdAt: new Date().toISOString(),
    },
  ];

  // Seed Loans (Home loan & Car loan)
  const homeLoanStartDate = new Date();
  homeLoanStartDate.setFullYear(homeLoanStartDate.getFullYear() - 2);

  liabilities = [
    {
      id: 'loan-home-sbi',
      userId: 'user-kavach-01',
      loanName: 'SBI Home Loan (Greenfield Residency)',
      principalAmount: 4500000,
      interestRate: 8.5,
      tenureMonths: 240,
      startDate: homeLoanStartDate.toISOString(),
      monthlyEMI: 39050,
      createdAt: new Date().toISOString(),
    },
    {
      id: 'loan-car-hdfc',
      userId: 'user-kavach-01',
      loanName: 'HDFC Vehicle Loan (Family SUV)',
      principalAmount: 650000,
      interestRate: 9.2,
      tenureMonths: 60,
      startDate: new Date(Date.now() - 365 * 86400000).toISOString(),
      monthlyEMI: 13540,
      createdAt: new Date().toISOString(),
    },
  ];
}

initDefaults();

// --- Mathematical Engine ---
function calculateDailyDebtCost(remainingPrincipal, annualRatePct) {
  if (remainingPrincipal <= 0 || annualRatePct <= 0) return 0;
  return (remainingPrincipal * annualRatePct) / (365 * 100);
}

function calculateEMI(principal, annualRatePct, tenureMonths) {
  if (principal <= 0 || tenureMonths <= 0) return 0;
  if (annualRatePct <= 0) return principal / tenureMonths;
  const monthlyRate = annualRatePct / (12 * 100);
  const factor = Math.pow(1 + monthlyRate, tenureMonths);
  return Math.round(((principal * monthlyRate * factor) / (factor - 1)) * 100) / 100;
}

function computeFullAmortization(loan, prepaymentAmount = 0, prepaymentMonth = 1) {
  const principal = loan.principalAmount;
  const rate = loan.interestRate;
  const tenure = loan.tenureMonths;
  const monthlyRate = rate / (12 * 100);
  const emi = loan.monthlyEMI || calculateEMI(principal, rate, tenure);

  const validStart = new Date(loan.startDate);
  const now = new Date();
  const monthsElapsed = Math.max(0, (now.getFullYear() - validStart.getFullYear()) * 12 + (now.getMonth() - validStart.getMonth()));

  // Baseline without prepayment
  let baselineTotalInterest = 0;
  let tempBal = principal;
  for (let m = 1; m <= tenure && tempBal > 0.01; m++) {
    const interest = tempBal * monthlyRate;
    const principalPaid = Math.min(tempBal, emi - interest);
    baselineTotalInterest += interest;
    tempBal -= principalPaid;
  }

  // Actual Schedule
  const monthlySchedule = [];
  let currentBalance = principal;
  let totalInterestWithPrepayment = 0;
  let actualMonthsTaken = 0;
  let currentRemainingPrincipal = principal;

  const maxMonths = Math.min(600, tenure + 12);
  for (let m = 1; m <= maxMonths && currentBalance > 0.01; m++) {
    const monthDate = new Date(validStart);
    monthDate.setMonth(monthDate.getMonth() + (m - 1));

    const startingBalance = currentBalance;
    const interest = monthlyRate > 0 ? startingBalance * monthlyRate : 0;
    let extra = (prepaymentAmount > 0 && m === prepaymentMonth) ? prepaymentAmount : 0;

    let regularPrincipal = emi - interest;
    if (regularPrincipal > startingBalance) regularPrincipal = startingBalance;

    let endingBalance = startingBalance - regularPrincipal;
    if (extra > 0) {
      if (extra > endingBalance) extra = endingBalance;
      endingBalance = Math.max(0, endingBalance - extra);
    }

    const roundedStart = Math.round(startingBalance * 100) / 100;
    const roundedInterest = Math.round(interest * 100) / 100;
    const roundedPrincipal = Math.round((regularPrincipal + extra) * 100) / 100;
    const roundedEnding = Math.round(endingBalance * 100) / 100;

    totalInterestWithPrepayment += roundedInterest;
    actualMonthsTaken = m;

    if (m === monthsElapsed) currentRemainingPrincipal = roundedEnding;

    monthlySchedule.push({
      monthIndex: m,
      date: monthDate.toISOString(),
      year: monthDate.getFullYear(),
      startingBalance: roundedStart,
      emi: Math.round(emi * 100) / 100,
      principalComponent: roundedPrincipal,
      interestComponent: roundedInterest,
      prepayment: extra,
      endingBalance: roundedEnding,
    });

    currentBalance = endingBalance;
  }

  // Yearly Aggregation
  const yearlyMap = new Map();
  for (const item of monthlySchedule) {
    if (!yearlyMap.has(item.year)) yearlyMap.set(item.year, []);
    yearlyMap.get(item.year).push(item);
  }

  const yearlySchedule = [];
  let yearCounter = 1;
  const sortedYears = Array.from(yearlyMap.keys()).sort((a, b) => a - b);

  for (const year of sortedYears) {
    const items = yearlyMap.get(year);
    const startBal = items[0].startingBalance;
    const endBal = items[items.length - 1].endingBalance;
    const yearPrincipal = items.reduce((sum, i) => sum + i.principalComponent, 0);
    const yearInterest = items.reduce((sum, i) => sum + i.interestComponent, 0);
    const yearEMI = items.reduce((sum, i) => sum + i.emi, 0);

    const sec24 = Math.min(200000, yearInterest);
    const sec80C = Math.min(150000, yearPrincipal);
    const totalDeduction = sec24 + sec80C;

    yearlySchedule.push({
      year,
      yearNumber: yearCounter++,
      monthsCount: items.length,
      startingBalance: Math.round(startBal * 100) / 100,
      totalPrincipalPaid: Math.round(yearPrincipal * 100) / 100,
      totalInterestPaid: Math.round(yearInterest * 100) / 100,
      totalEMIPaid: Math.round(yearEMI * 100) / 100,
      endingBalance: Math.round(endBal * 100) / 100,
      taxSavings: {
        section24EligibleInterest: Math.round(sec24),
        section80CEligiblePrincipal: Math.round(sec80C),
        totalDeduction: Math.round(totalDeduction),
        estimatedTaxSavedAt30Pct: Math.round(totalDeduction * 0.30),
        estimatedTaxSavedAt20Pct: Math.round(totalDeduction * 0.20),
      },
    });
  }

  const monthsShaved = Math.max(0, tenure - actualMonthsTaken);
  const yearsShaved = Math.round((monthsShaved / 12) * 10) / 10;
  const interestSaved = Math.max(0, baselineTotalInterest - totalInterestWithPrepayment);
  const activeBal = currentRemainingPrincipal > 0 ? currentRemainingPrincipal : principal;
  const dailyCost = calculateDailyDebtCost(activeBal, rate);

  return {
    loan: {
      id: loan.id,
      loanName: loan.loanName,
      principalAmount: principal,
      interestRate: rate,
      tenureMonths: tenure,
      startDate: loan.startDate,
      monthlyEMI: emi,
      currentRemainingPrincipal: Math.round(activeBal * 100) / 100,
    },
    dailyMetrics: {
      remainingPrincipal: Math.round(activeBal * 100) / 100,
      dailyInterestCost: Math.round(dailyCost * 100) / 100,
      annualInterestCost: Math.round(dailyCost * 365 * 100) / 100,
      coffeeEquivalentPerDay: Math.round((dailyCost / 150) * 10) / 10,
    },
    prepaymentSimulation: {
      hasPrepayment: prepaymentAmount > 0,
      prepaymentAmount,
      prepaymentMonth,
      originalTenureMonths: tenure,
      newTenureMonths: actualMonthsTaken,
      monthsShaved,
      yearsShaved,
      originalTotalInterest: Math.round(baselineTotalInterest * 100) / 100,
      newTotalInterest: Math.round(totalInterestWithPrepayment * 100) / 100,
      interestSaved: Math.round(interestSaved * 100) / 100,
    },
    monthlySchedule,
    yearlySchedule,
  };
}

// --- API Endpoints ---

// 1. Dashboard Overview
app.get('/api/dashboard', (req, res) => {
  const tomorrowKey = new Date(Date.now() + 86400000).toISOString().split('T')[0];
  const tomorrowRadars = upcomingRadars.filter(r => r.dueDate.startsWith(tomorrowKey));
  const unpaid = tomorrowRadars.filter(r => !r.isPaid);

  let totalDailyDebtCost = 0;
  for (const l of liabilities) {
    const amort = computeFullAmortization(l);
    totalDailyDebtCost += amort.dailyMetrics.dailyInterestCost;
  }

  res.json({
    streak: 14,
    todayCheckIn: null,
    isTodayLogged: false,
    tomorrowRadars,
    tomorrowUnpaidCount: unpaid.length,
    tomorrowTotalAmount: unpaid.reduce((s, r) => s + r.amount, 0),
    vaultOverview: {
      activeLoansCount: liabilities.length,
      totalDailyDebtCost: Math.round(totalDailyDebtCost * 100) / 100,
    },
  });
});

// 2. Daily Logs
app.get('/api/daily-logs', (req, res) => {
  res.json({ streak: 14, logs: dailyLogs });
});

app.post('/api/daily-logs', (req, res) => {
  const { totalSpent, categoriesBreakdown, notes } = req.body;
  const newLog = {
    id: `log-${Date.now()}`,
    userId: 'user-kavach-01',
    logDate: new Date().toISOString().split('T')[0],
    totalSpent: Number(totalSpent) || 0,
    categoriesBreakdown: categoriesBreakdown || {},
    notes: notes || '',
    createdAt: new Date().toISOString(),
  };
  dailyLogs.unshift(newLog);
  res.status(201).json({ message: 'Daily check-in completed', log: newLog, streak: 15 });
});

// 3. Tomorrow's Radar & Reminders
app.get('/api/radar/tomorrow', (req, res) => {
  const tomorrowKey = new Date(Date.now() + 86400000).toISOString().split('T')[0];
  const items = upcomingRadars.filter(r => r.dueDate.startsWith(tomorrowKey));
  res.json({ items, unpaidCount: items.filter(r => !r.isPaid).length });
});

app.get('/api/radar', (req, res) => {
  res.json({ all: upcomingRadars });
});

app.post('/api/radar', (req, res) => {
  const { title, amount, dueDate, recurringType, category } = req.body;
  const item = {
    id: `radar-${Date.now()}`,
    userId: 'user-kavach-01',
    title: String(title),
    amount: Number(amount),
    dueDate: new Date(dueDate).toISOString(),
    isPaid: false,
    recurringType: recurringType || 'NONE',
    category: category || 'General',
    createdAt: new Date().toISOString(),
  };
  upcomingRadars.push(item);
  res.status(201).json({ message: 'Bill added to radar', item });
});

app.patch('/api/radar/:id', (req, res) => {
  const item = upcomingRadars.find(r => r.id === req.params.id);
  if (!item) return res.status(404).json({ error: 'Item not found' });
  item.isPaid = !item.isPaid;
  res.json({ message: `Bill marked as ${item.isPaid ? 'paid' : 'unpaid'}`, item });
});

app.delete('/api/radar/:id', (req, res) => {
  upcomingRadars = upcomingRadars.filter(r => r.id !== req.params.id);
  res.json({ message: 'Bill removed from radar' });
});

// 4. Liabilities Vault & Multi-Granular Amortization
app.get('/api/liabilities', (req, res) => {
  res.json({ loans: liabilities });
});

app.post('/api/liabilities', (req, res) => {
  const { loanName, principalAmount, interestRate, tenureMonths, startDate } = req.body;
  const emi = calculateEMI(Number(principalAmount), Number(interestRate), Number(tenureMonths));
  const loan = {
    id: `loan-${Date.now()}`,
    userId: 'user-kavach-01',
    loanName,
    principalAmount: Number(principalAmount),
    interestRate: Number(interestRate),
    tenureMonths: Number(tenureMonths),
    startDate: startDate || new Date().toISOString(),
    monthlyEMI: emi,
    createdAt: new Date().toISOString(),
  };
  liabilities.push(loan);
  res.status(201).json({ message: 'Loan created in vault', loan });
});

app.get('/api/liabilities/:id/amortization', (req, res) => {
  const loan = liabilities.find(l => l.id === req.params.id);
  if (!loan) return res.status(404).json({ error: 'Loan not found' });

  const prepaymentAmount = Number(req.query.prepaymentAmount) || 0;
  const prepaymentMonth = Number(req.query.prepaymentMonth) || 1;

  const result = computeFullAmortization(loan, prepaymentAmount, prepaymentMonth);
  res.json(result);
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`[FamilyVault / Kavach] Express API Server running on http://localhost:${PORT}`);
  });
}

module.exports = app;
