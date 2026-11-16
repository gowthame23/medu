import { NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function POST() {
  try {
    const result = dataStore.autoSyncExternalBills();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error auto-syncing external bills:', error);
    return NextResponse.json({ error: 'Failed to auto-sync bills' }, { status: 500 });
  }
}
