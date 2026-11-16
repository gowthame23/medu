import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function PATCH(req: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    let body: any = {};
    try {
      body = await req.json();
    } catch {
      // empty body means toggle
    }

    if (body.amount !== undefined && !isNaN(Number(body.amount))) {
      const updated = dataStore.updateRadarAmount(id, Number(body.amount));
      if (!updated) return NextResponse.json({ error: 'Radar item not found' }, { status: 404 });
      return NextResponse.json({ message: 'Bill amount updated', item: updated });
    }

    const updated = dataStore.toggleRadarPaid(id, {
      payerName: body.paidBy,
      paymentMethod: body.paymentMethod,
      syncSource: body.syncSource,
      paymentRef: body.paymentRef,
    });
    if (!updated) {
      return NextResponse.json({ error: 'Radar item not found' }, { status: 404 });
    }
    return NextResponse.json({
      message: `Bill marked as ${updated.isPaid ? 'paid' : 'unpaid'}`,
      item: updated,
    });
  } catch (error) {
    console.error('Error toggling radar item:', error);
    return NextResponse.json({ error: 'Failed to update reminder' }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const deleted = dataStore.deleteRadar(id);
    if (!deleted) {
      return NextResponse.json({ error: 'Radar item not found' }, { status: 404 });
    }
    return NextResponse.json({ message: 'Bill reminder removed from radar' });
  } catch (error) {
    console.error('Error deleting radar item:', error);
    return NextResponse.json({ error: 'Failed to delete reminder' }, { status: 500 });
  }
}
