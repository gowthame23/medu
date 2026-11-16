import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(req: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const { searchParams } = new URL(req.url);

    const prepaymentAmount = searchParams.get('prepaymentAmount')
      ? Number(searchParams.get('prepaymentAmount'))
      : 0;

    const prepaymentMonth = searchParams.get('prepaymentMonth')
      ? Number(searchParams.get('prepaymentMonth'))
      : 1;

    const result = dataStore.getAmortizationForLoan(id, {
      prepaymentAmount,
      prepaymentMonth,
    });

    if (!result) {
      return NextResponse.json(
        { error: 'Loan not found in Liabilities Vault' },
        { status: 404 }
      );
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error computing amortization:', error);
    return NextResponse.json(
      { error: 'Failed to compute amortization schedule' },
      { status: 500 }
    );
  }
}
