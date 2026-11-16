import { NextRequest, NextResponse } from 'next/server';
import { dataStore } from '@/lib/dataStore';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { phone, email } = body;

    if (!phone || !email) {
      return NextResponse.json(
        { error: 'Phone number and email address are required' },
        { status: 400 }
      );
    }

    // Realistic discovery response simulating RBI Account Aggregator (AA) & NPCI BBPS
    const discoveredData = {
      user: {
        phone: String(phone),
        email: String(email),
        name: 'Gowtham',
        kycStatus: 'Verified (Aadhaar & PAN linked)',
      },
      sourcesScanned: [
        { name: 'RBI Account Aggregator (Finvu / Setu)', status: 'Connected', recordsFound: 3 },
        { name: 'NPCI BBPS Central Directory', status: 'Connected', recordsFound: 2 },
        { name: 'UPI AutoPay e-Mandate Registry', status: 'Connected', recordsFound: 2 },
      ],
      discoveredBills: [
        {
          title: 'Electricity Bill (BESCOM)',
          amount: 2450,
          dueDate: new Date(Date.now() + 86400000).toISOString(),
          category: 'Utilities',
          consumerNumber: 'BESCOM-CA #4928120',
          assignedTo: 'Gowtham' as const,
          recurringType: 'MONTHLY' as const,
          source: 'BBPS Central Utility Registry',
        },
        {
          title: 'Airtel Fiber Broadband',
          amount: 1179,
          dueDate: new Date(Date.now() + 86400000).toISOString(),
          category: 'Utilities',
          consumerNumber: 'Airtel-ID #08041920',
          assignedTo: 'Gowtham' as const,
          recurringType: 'MONTHLY' as const,
          source: 'BBPS Telecom Discovery',
        },
        {
          title: 'Netflix Premium (UPI Autopay)',
          amount: 649,
          dueDate: new Date(Date.now() + 86400000).toISOString(),
          category: 'Subscriptions',
          consumerNumber: 'UPI-MANDATE #NF-8829',
          assignedTo: 'Shared' as const,
          recurringType: 'MONTHLY' as const,
          source: 'NPCI UPI AutoPay Mandate',
        },
        {
          title: 'Apartment Maintenance',
          amount: 4200,
          dueDate: new Date(Date.now() + 3 * 86400000).toISOString(),
          category: 'Housing',
          consumerNumber: 'Flat-402-Society',
          assignedTo: 'Priya' as const,
          recurringType: 'MONTHLY' as const,
          source: 'Society Recurring e-Mandate',
        },
      ],
      discoveredLiabilities: [
        {
          loanName: 'SBI Home Loan (Greenfield Residency)',
          principalAmount: 4500000,
          interestRate: 8.5,
          tenureMonths: 240,
          startDate: new Date(Date.now() - 2 * 365 * 86400000).toISOString(),
          source: 'Credit Bureau / Account Aggregator',
        },
        {
          loanName: 'HDFC Vehicle Loan (Family SUV)',
          principalAmount: 650000,
          interestRate: 9.2,
          tenureMonths: 60,
          startDate: new Date(Date.now() - 365 * 86400000).toISOString(),
          source: 'Credit Bureau / Account Aggregator',
        },
      ],
    };

    return NextResponse.json(discoveredData);
  } catch (error) {
    console.error('Error during auto-discovery:', error);
    return NextResponse.json({ error: 'Auto-discovery failed' }, { status: 500 });
  }
}
