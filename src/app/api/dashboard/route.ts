import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const mode = (searchParams.get('mode') === 'family' ? 'family' : 'individual') as 'individual' | 'family';
    const userId = searchParams.get('userId') || undefined;
    const overview = dataStore.getDashboardOverview(mode, userId);
    return NextResponse.json(overview);
  } catch (error) {
    console.error('Error fetching dashboard overview:', error);
    return NextResponse.json(
      { error: 'Failed to fetch dashboard data' },
      { status: 500 }
    );
  }
}
