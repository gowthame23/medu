'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Building,
  Sparkles,
  Sliders,
  DollarSign,
  Coffee,
  CheckCircle,
  Plus,
  RefreshCw,
  Lock,
  Unlock,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';
import { AmortizationResult } from '@/lib/amortization';
import { LiabilityRecord, CURRENT_USER } from '@/lib/dataStore';

interface LiabilitiesVaultViewProps {
  loans: LiabilityRecord[];
  onOpenAddLoan: () => void;
  onRefreshLoans: () => void;
  userName?: string;
}

export default function LiabilitiesVaultView({
  loans,
  onOpenAddLoan,
  onRefreshLoans,
  userName = 'Gowtham',
}: LiabilitiesVaultViewProps) {
  const [selectedLoanId, setSelectedLoanId] = useState<string>(loans[0]?.id || '');
  const [granularTab, setGranularTab] = useState<'daily' | 'monthly' | 'yearly'>('daily');

  // Prepayment Simulator state
  const [prepaymentInput, setPrepaymentInput] = useState<string>('50000');
  const [amortizationData, setAmortizationData] = useState<AmortizationResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isVaultLocked, setIsVaultLocked] = useState<boolean>(false);

  useEffect(() => {
    if (loans.length > 0 && (!selectedLoanId || !loans.some(l => l.id === selectedLoanId))) {
      setSelectedLoanId(loans[0].id);
    }
  }, [loans, selectedLoanId]);

  useEffect(() => {
    if (!selectedLoanId) return;

    let isMounted = true;
    setIsLoading(true);

    const prepVal = parseFloat(prepaymentInput) || 0;
    const url = `/api/liabilities/${selectedLoanId}/amortization?prepaymentAmount=${prepVal}&prepaymentMonth=1`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (isMounted) {
          setAmortizationData(data);
          setIsLoading(false);
        }
      })
      .catch(err => {
        console.error('Error loading amortization:', err);
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedLoanId, prepaymentInput]);

  return (
    <div className="space-y-4 px-4 pt-3 pb-24 animate-fade-in">
      {/* 1. STRICT PRIVACY & BIOMETRIC GATE BANNER */}
      <div className="p-4 rounded-3xl bg-stone-900 text-white shadow-sm space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-stone-800 flex items-center justify-center text-emerald-400 shrink-0">
              {isVaultLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-white">Private Liabilities Vault</span>
                <span className="text-[9px] bg-emerald-900 text-emerald-300 font-bold px-1.5 py-0.2 rounded">
                  Sandboxed
                </span>
              </div>
              <p className="text-[10px] text-stone-400">
                100% Private to {userName} • Zero Family Access
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsVaultLocked(!isVaultLocked)}
            className="px-2.5 py-1 text-[10px] font-bold rounded-xl bg-stone-800 border border-stone-700 text-stone-300 flex items-center gap-1 active:scale-95"
          >
            <KeyRound className="w-3 h-3 text-emerald-400" />
            <span>{isVaultLocked ? 'Unlock' : 'Lock Vault'}</span>
          </button>
        </div>

        <p className="text-[10px] text-stone-400 leading-relaxed border-t border-stone-800 pt-2">
          Debt is simply rented money and a math problem. This view is strictly isolated from your Family Shared Hub to ensure domestic peace of mind.
        </p>
      </div>

      {isVaultLocked ? (
        <div className="py-16 text-center bg-white rounded-3xl p-6 border border-stone-200 space-y-3">
          <Lock className="w-10 h-10 text-stone-400 mx-auto" />
          <h3 className="text-sm font-bold text-stone-900">Liabilities Vault is Gated</h3>
          <p className="text-xs text-stone-500 max-w-xs mx-auto">
            Your personal loans and amortization models are protected. Tap unlock to view.
          </p>
          <button
            onClick={() => setIsVaultLocked(false)}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-800 text-white active:scale-95 shadow-xs"
          >
            Authenticate &amp; Unlock
          </button>
        </div>
      ) : (
        <>
          {/* 2. LOAN PICKER CHIPS */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
            {loans.map(loan => (
              <button
                key={loan.id}
                onClick={() => setSelectedLoanId(loan.id)}
                className={`px-3 py-1.5 rounded-2xl text-xs font-bold transition-all whitespace-nowrap shrink-0 border ${
                  selectedLoanId === loan.id
                    ? 'bg-stone-900 text-white border-stone-900 shadow-xs'
                    : 'bg-white text-stone-700 border-stone-200'
                }`}
              >
                {loan.loanName} ({loan.interestRate}%)
              </button>
            ))}

            <button
              onClick={onOpenAddLoan}
              className="px-3 py-1.5 rounded-2xl text-xs font-bold bg-white text-emerald-800 border border-emerald-200 flex items-center gap-1 shrink-0"
            >
              <Plus className="w-3.5 h-3.5" /> Add Personal Loan
            </button>
          </div>

          {/* 3. MULTI-GRANULAR VIEW SWITCHER PILLS (Daily, Monthly, Yearly) */}
          <div className="grid grid-cols-3 p-1 bg-stone-200/80 rounded-2xl text-xs font-bold text-stone-600">
            <button
              onClick={() => setGranularTab('daily')}
              className={`py-1.5 rounded-xl transition-all ${
                granularTab === 'daily' ? 'bg-white text-stone-900 shadow-xs font-extrabold' : 'hover:text-stone-900'
              }`}
            >
              1. Daily Cost
            </button>
            <button
              onClick={() => setGranularTab('monthly')}
              className={`py-1.5 rounded-xl transition-all ${
                granularTab === 'monthly' ? 'bg-white text-stone-900 shadow-xs font-extrabold' : 'hover:text-stone-900'
              }`}
            >
              2. Prepayment
            </button>
            <button
              onClick={() => setGranularTab('yearly')}
              className={`py-1.5 rounded-xl transition-all ${
                granularTab === 'yearly' ? 'bg-white text-stone-900 shadow-xs font-extrabold' : 'hover:text-stone-900'
              }`}
            >
              3. Tax Shield
            </button>
          </div>

          {/* 4. CONTENT CARDS */}
          {isLoading && !amortizationData ? (
            <div className="py-12 text-center text-xs text-stone-400 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Crunching mathematical models...</span>
            </div>
          ) : amortizationData ? (
            <div className="space-y-4">
              {/* TAB 1: DAILY VIEW */}
              {granularTab === 'daily' && (
                <div className="space-y-3">
                  <div className="bg-white rounded-3xl p-6 border border-stone-200 text-center space-y-2 shadow-xs">
                    <span className="text-[10px] font-bold uppercase text-stone-400 tracking-wider">
                      Daily Cost of Debt Formula: (P × r) / (365 × 100)
                    </span>
                    <div className="text-4xl font-black text-stone-900">
                      ₹{amortizationData.dailyMetrics.dailyInterestCost.toLocaleString('en-IN')}
                      <span className="text-sm font-normal text-stone-500"> /day</span>
                    </div>
                    <p className="text-xs text-stone-600 font-medium">
                      Current daily interest running on{' '}
                      <span className="font-bold text-stone-900">
                        {amortizationData.loan.loanName}
                      </span>
                    </p>
                  </div>

                  {/* Objective Financial Metrics */}
                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="p-3.5 rounded-2xl bg-white border border-stone-200 text-center">
                      <div className="text-[10px] text-stone-400 font-bold uppercase">Annual Interest</div>
                      <div className="text-base font-black text-stone-800 mt-0.5">
                        ₹{(amortizationData.dailyMetrics.annualInterestCost / 1000).toFixed(1)}k /yr
                      </div>
                      <div className="text-[10px] text-stone-500 mt-0.5">Running yearly cost</div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-white border border-stone-200 text-center">
                      <div className="text-[10px] text-stone-400 font-bold uppercase">Active Principal</div>
                      <div className="text-base font-black text-stone-800 mt-0.5">
                        ₹{(amortizationData.dailyMetrics.remainingPrincipal / 100000).toFixed(1)}L
                      </div>
                      <div className="text-[10px] text-stone-500 mt-0.5">Remaining balance</div>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-100 flex items-start gap-2.5">
                    <CheckCircle className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                    <p className="text-xs text-emerald-950 leading-relaxed">
                      Seeing debt as ₹{amortizationData.dailyMetrics.dailyInterestCost}/day shrinks it to human proportions. Every extra lump-sum cuts this daily cost permanently.
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 2: MONTHLY VIEW & PREPAYMENT SIMULATOR */}
              {granularTab === 'monthly' && (
                <div className="bg-white rounded-3xl p-5 border border-stone-200 space-y-4 shadow-xs">
                  <div>
                    <h4 className="text-xs font-bold text-stone-900 uppercase tracking-wide">
                      Interactive Prepayment Simulator
                    </h4>
                    <p className="text-[11px] text-stone-500">
                      Test adding extra lump sums and see months shaved off.
                    </p>
                  </div>

                  {/* Quick Amount Pills */}
                  <div className="grid grid-cols-4 gap-1.5">
                    {[25000, 50000, 100000, 200000].map(amt => (
                      <button
                        key={amt}
                        onClick={() => setPrepaymentInput(String(amt))}
                        className={`py-2 text-xs font-bold rounded-xl border transition-all active:scale-95 ${
                          prepaymentInput === String(amt)
                            ? 'bg-emerald-800 text-white border-emerald-800 shadow-2xs font-extrabold'
                            : 'bg-stone-50 text-stone-700 border-stone-200'
                        }`}
                      >
                        +₹{amt / 1000}k
                      </button>
                    ))}
                  </div>

                  {/* Custom Input */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-stone-500">Amount:</span>
                    <input
                      type="number"
                      value={prepaymentInput}
                      onChange={e => setPrepaymentInput(e.target.value)}
                      className="flex-1 px-3 py-1.5 text-xs font-bold rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
                    />
                  </div>

                  {/* Savings Cards */}
                  {amortizationData.prepaymentSimulation.hasPrepayment && (
                    <div className="space-y-2 pt-2 border-t border-stone-100">
                      <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] font-bold text-emerald-800 uppercase">
                            Tenure Shaved Off
                          </div>
                          <div className="text-lg font-black text-emerald-950">
                            {amortizationData.prepaymentSimulation.monthsShaved} Months Earlier
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] font-bold text-emerald-800 uppercase">
                            Interest Saved
                          </div>
                          <div className="text-lg font-black text-emerald-950">
                            ₹{amortizationData.prepaymentSimulation.interestSaved.toLocaleString('en-IN')}
                          </div>
                        </div>
                      </div>

                      <div className="text-center text-[11px] text-stone-500 font-medium">
                        New Payoff: {amortizationData.prepaymentSimulation.newTenureMonths} Months (down from {amortizationData.loan.tenureMonths})
                      </div>
                    </div>
                  )}

                  {/* Amortization Table Summary */}
                  <div className="pt-2 border-t border-stone-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-stone-900">Upcoming Monthly Schedule</span>
                      <span className="text-[10px] text-stone-500 font-mono">EMI: ₹{amortizationData.loan.monthlyEMI.toLocaleString('en-IN')}/mo</span>
                    </div>

                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {amortizationData.monthlySchedule.slice(0, 6).map(row => (
                        <div
                          key={row.monthIndex}
                          className="p-2 rounded-xl bg-stone-50 border border-stone-200/70 flex items-center justify-between text-xs"
                        >
                          <span className="font-semibold text-stone-800">
                            Month #{row.monthIndex}
                          </span>
                          <span className="text-stone-500 text-[11px]">
                            Principal: <strong className="text-emerald-800">₹{row.principalComponent.toLocaleString('en-IN')}</strong>
                          </span>
                          <span className="text-stone-500 text-[11px]">
                            Interest: <strong className="text-amber-800">₹{row.interestComponent.toLocaleString('en-IN')}</strong>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: YEARLY VIEW & INDIAN TAX SHIELD */}
              {granularTab === 'yearly' && (
                <div className="bg-white rounded-3xl p-5 border border-stone-200 space-y-3 shadow-xs">
                  <div>
                    <h4 className="text-xs font-bold text-stone-900 uppercase">
                      Indian Income Tax Shield (Sec 24 &amp; 80C)
                    </h4>
                    <p className="text-[11px] text-stone-500">
                      Eligible tax deductions on home loan repayments
                    </p>
                  </div>

                  <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-stone-600">Section 24(b) - Interest Deduction:</span>
                      <span className="font-bold text-stone-900">Up to ₹2,00,000 / yr</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-stone-600">Section 80C - Principal Deduction:</span>
                      <span className="font-bold text-stone-900">Up to ₹1,50,000 / yr</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-emerald-800 text-white text-center shadow-xs">
                    <div className="text-[10px] font-bold text-emerald-200 uppercase tracking-wide">
                      Estimated Annual Tax Shield
                    </div>
                    <div className="text-2xl font-black mt-0.5">~₹1,05,000 / year</div>
                    <div className="text-[10px] text-emerald-100 mt-0.5">Under 30% tax slab</div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
