import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { radarId, payerUserId, payerName, paymentRef, paymentMethod } = body;

    if (!radarId) {
      return NextResponse.json({ error: 'radarId is required' }, { status: 400 });
    }

    const updated = dataStore.reconcileUPIPayment(radarId, {
      payerUserId,
      payerName,
      paymentRef,
      paymentMethod,
    });

    if (!updated) {
      return NextResponse.json({ error: 'Bill reminder not found' }, { status: 404 });
    }

    return NextResponse.json({
      message: 'Payment successfully reconciled via UPI deep-link',
      item: updated,
    });
  } catch (error) {
    console.error('Error reconciling UPI payment:', error);
    return NextResponse.json({ error: 'Failed to reconcile payment' }, { status: 500 });
  }
}
