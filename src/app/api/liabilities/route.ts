import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';
import { computeAmortization } from '@/lib/amortization';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const mode = searchParams.get('mode');

    // Strict privacy boundary: Zero loan leakage into Family Shared Hub!
    if (mode === 'family') {
      return NextResponse.json(
        {
          error: 'Privacy Violation Prevented: Liabilities Vault is strictly personal and sandboxed. Family views never display personal loans or debt.',
          access: 'RESTRICTED',
        },
        { status: 403 }
      );
    }

    const userId = searchParams.get('userId') || undefined;
    const loans = dataStore.getPrivateLiabilities(userId);

    const enriched = loans.map(loan => {
      const amort = computeAmortization(loan);
      return {
        ...loan,
        remainingPrincipal: amort.dailyMetrics.remainingPrincipal,
        dailyCostOfDebt: amort.dailyMetrics.dailyInterestCost,
        annualInterestCost: amort.dailyMetrics.annualInterestCost,
      };
    });

    const totalDailyCost = enriched.reduce((sum, l) => sum + l.dailyCostOfDebt, 0);
    const totalRemaining = enriched.reduce((sum, l) => sum + l.remainingPrincipal, 0);

    return NextResponse.json({
      loans: enriched,
      aggregate: {
        totalLoans: enriched.length,
        totalRemainingPrincipal: Math.round(totalRemaining),
        totalDailyDebtCost: Math.round(totalDailyCost * 100) / 100,
        coffeeEquivalent: Math.round((totalDailyCost / 150) * 10) / 10,
      },
    });
  } catch (error) {
    console.error('Error fetching liabilities:', error);
    return NextResponse.json({ error: 'Failed to fetch liabilities' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { loanName, principalAmount, interestRate, tenureMonths, startDate, monthlyEMI, userId } = body;

    if (!loanName || !principalAmount || !interestRate || !tenureMonths) {
      return NextResponse.json(
        { error: 'Loan name, principal amount, annual interest rate, and tenure months are required' },
        { status: 400 }
      );
    }

    const created = dataStore.createLiability({
      userId: userId || undefined,
      loanName: String(loanName).trim(),
      principalAmount: Number(principalAmount),
      interestRate: Number(interestRate),
      tenureMonths: Number(tenureMonths),
      startDate: startDate || new Date().toISOString(),
      monthlyEMI: monthlyEMI ? Number(monthlyEMI) : undefined,
    });

    return NextResponse.json(
      {
        message: 'Personal loan added to Private Liabilities Vault safely',
        loan: created,
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error adding liability:', error);
    return NextResponse.json({ error: 'Failed to add liability' }, { status: 500 });
  }
}
