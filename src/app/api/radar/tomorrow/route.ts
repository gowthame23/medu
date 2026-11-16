import { NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function GET() {
  try {
    const tomorrowRadars = dataStore.getTomorrowRadars();
    const unpaidTomorrow = tomorrowRadars.filter(r => !r.isPaid);
    const totalAmount = unpaidTomorrow.reduce((sum, r) => sum + r.amount, 0);

    return NextResponse.json({
      targetDate: new Date(Date.now() + 86400000).toISOString().split('T')[0],
      items: tomorrowRadars,
      unpaidCount: unpaidTomorrow.length,
      totalAmount: Math.round(totalAmount * 100) / 100,
      peaceOfMindStatus: unpaidTomorrow.length === 0 ? 'Clear horizon' : `${unpaidTomorrow.length} bill(s) due tomorrow`,
    });
  } catch (error) {
    console.error('Error fetching tomorrow radar:', error);
    return NextResponse.json({ error: 'Failed to fetch tomorrow radar' }, { status: 500 });
  }
}
