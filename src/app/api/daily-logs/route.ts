import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const userId = searchParams.get('userId') || undefined;

    const logs = dataStore.getAllDailyLogs(userId);
    const streak = dataStore.getStreak(userId);
    const todayCheckIn = dataStore.getTodayCheckIn(userId);

    return NextResponse.json({
      streak,
      todayCheckIn,
      isTodayLogged: !!todayCheckIn,
      logs,
    });
  } catch (error) {
    console.error('Error fetching daily logs:', error);
    return NextResponse.json({ error: 'Failed to fetch daily logs' }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { totalSpent, categoriesBreakdown, notes, logDate, userId } = body;

    if (totalSpent === undefined || isNaN(Number(totalSpent))) {
      return NextResponse.json(
        { error: 'Valid totalSpent amount is required' },
        { status: 400 }
      );
    }

    const savedLog = dataStore.saveDailyLog({
      userId: userId || undefined,
      totalSpent: Number(totalSpent),
      categoriesBreakdown: categoriesBreakdown || {},
      notes: notes || '',
      logDate: logDate,
    });

    const newStreak = dataStore.getStreak(userId);

    return NextResponse.json(
      {
        message: 'Daily check-in logged successfully! Peace of mind restored.',
        log: savedLog,
        streak: newStreak,
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error saving daily log:', error);
    return NextResponse.json({ error: 'Failed to save daily check-in' }, { status: 500 });
  }
}
