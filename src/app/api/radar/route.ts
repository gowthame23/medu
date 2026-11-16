import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const mode = searchParams.get('mode') === 'family' ? 'family' : 'individual';
    const userId = searchParams.get('userId') || undefined;

    const allRadars = mode === 'family' ? dataStore.getFamilyRadars() : dataStore.getIndividualRadars(userId);
    const tomorrowRadars = dataStore.getTomorrowRadars(mode, userId);

    return NextResponse.json({
      mode,
      all: allRadars,
      tomorrow: tomorrowRadars,
      unpaidCount: allRadars.filter(r => !r.isPaid).length,
    });
  } catch (error) {
    console.error('Error fetching radar reminders:', error);
    return NextResponse.json({ error: 'Failed to fetch radar items' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { title, amount, dueDate, recurringType, category, consumerNumber, familyGroupId, userId } = body;

    if (!title || !dueDate || amount === undefined || isNaN(Number(amount))) {
      return NextResponse.json(
        { error: 'Title, valid amount, and dueDate are required' },
        { status: 400 }
      );
    }

    const created = dataStore.createRadar({
      title: String(title).trim(),
      amount: Number(amount),
      dueDate: String(dueDate),
      recurringType: recurringType || 'NONE',
      category: category || 'Utilities',
      consumerNumber: consumerNumber ? String(consumerNumber).trim() : undefined,
      familyGroupId: familyGroupId,
      userId: userId,
    });

    return NextResponse.json(
      {
        message: 'Upcoming bill added to Radar successfully',
        item: created,
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error creating radar reminder:', error);
    return NextResponse.json({ error: 'Failed to create reminder' }, { status: 500 });
  }
}
