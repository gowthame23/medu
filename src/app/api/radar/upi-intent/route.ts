import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { radarId, payerUserId } = body;

    if (!radarId) {
      return NextResponse.json({ error: 'radarId is required' }, { status: 400 });
    }

    const intent = dataStore.generateUPIIntent(radarId, payerUserId);
    if (!intent) {
      return NextResponse.json({ error: 'Bill reminder not found' }, { status: 404 });
    }

    return NextResponse.json(intent);
  } catch (error) {
    console.error('Error generating UPI intent:', error);
    return NextResponse.json({ error: 'Failed to generate UPI intent' }, { status: 500 });
  }
}
