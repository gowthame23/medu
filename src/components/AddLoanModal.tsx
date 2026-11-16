'use client';

import React, { useState, useEffect } from 'react';
import { X, Building, Plus } from 'lucide-react';
import { calculateEMI } from '@/lib/amortization';

interface AddLoanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userId?: string;
}

export default function AddLoanModal({ isOpen, onClose, onSuccess, userId }: AddLoanModalProps) {
  const [loanName, setLoanName] = useState('');
  const [principalAmount, setPrincipalAmount] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [tenureYears, setTenureYears] = useState('15');
  const [startDate, setStartDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setStartDate(new Date().toISOString().split('T')[0]);
  }, []);

  if (!isOpen) return null;

  const tenureMonths = Math.max(1, (parseFloat(tenureYears) || 0) * 12);
  const estimatedEMI =
    principalAmount && interestRate && tenureMonths
      ? calculateEMI(parseFloat(principalAmount), parseFloat(interestRate), tenureMonths)
      : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loanName.trim() || !principalAmount || !interestRate || !tenureYears) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/liabilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId,
          loanName: loanName.trim(),
          principalAmount: parseFloat(principalAmount),
          interestRate: parseFloat(interestRate),
          tenureMonths,
          startDate: new Date(startDate).toISOString(),
          monthlyEMI: estimatedEMI,
        }),
      });

      if (res.ok) {
        onSuccess();
        onClose();
        setLoanName('');
        setPrincipalAmount('');
        setInterestRate('');
      }
    } catch (err) {
      console.error('Error adding loan:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-xs">
      <div className="relative w-full max-w-md bg-white rounded-3xl shadow-xl border border-stone-200/80 overflow-hidden">
        <div className="px-6 pt-6 pb-4 border-b border-stone-100 flex items-center justify-between bg-stone-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-stone-200 text-stone-700 flex items-center justify-center">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900">Add Loan to Vault</h2>
              <p className="text-xs text-stone-500">Track amortization and test prepayment savings</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full text-stone-400 hover:text-stone-700 hover:bg-stone-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Loan Name & Bank
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Home Loan (SBI) or Car Loan (HDFC)"
              value={loanName}
              onChange={e => setLoanName(e.target.value)}
              className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Principal Amount (₹)
              </label>
              <input
                type="number"
                required
                min="1000"
                step="any"
                placeholder="₹30,00,000"
                value={principalAmount}
                onChange={e => setPrincipalAmount(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Annual Interest Rate (%)
              </label>
              <input
                type="number"
                required
                min="0.1"
                max="50"
                step="0.01"
                placeholder="8.5"
                value={interestRate}
                onChange={e => setInterestRate(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Tenure (Years)
              </label>
              <input
                type="number"
                required
                min="0.5"
                max="40"
                step="0.5"
                value={tenureYears}
                onChange={e => setTenureYears(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                required
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
          </div>

          {estimatedEMI > 0 && (
            <div className="p-3 bg-stone-50 rounded-xl border border-stone-200 text-xs flex items-center justify-between">
              <span className="text-stone-500">Calculated Monthly EMI:</span>
              <span className="font-bold text-stone-900">
                ₹{estimatedEMI.toLocaleString('en-IN')}/mo
              </span>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs rounded-xl text-stone-600 hover:bg-stone-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2.5 text-xs font-medium rounded-xl bg-stone-900 text-white hover:bg-stone-800 transition-all flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Saving...' : 'Add Loan Safely'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
