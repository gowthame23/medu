import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(req: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const loan = dataStore.getLiabilityById(id);
    if (!loan) {
      return NextResponse.json({ error: 'Loan not found in vault' }, { status: 404 });
    }
    return NextResponse.json(loan);
  } catch (error) {
    console.error('Error fetching loan:', error);
    return NextResponse.json({ error: 'Failed to retrieve loan details' }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const deleted = dataStore.deleteLiability(id);
    if (!deleted) {
      return NextResponse.json({ error: 'Loan not found in vault' }, { status: 404 });
    }
    return NextResponse.json({ message: 'Loan safely removed from vault' });
  } catch (error) {
    console.error('Error deleting loan:', error);
    return NextResponse.json({ error: 'Failed to remove loan' }, { status: 500 });
  }
}
