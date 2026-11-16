"use client";

import React, { useState } from "react";
import { X, Building, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface AddLoanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddLoanModal({ isOpen, onClose, onSuccess }: AddLoanModalProps) {
  const [loanName, setLoanName] = useState("");
  const [principalAmount, setPrincipalAmount] = useState("");
  const [interestRate, setInterestRate] = useState("");
  const [tenureYears, setTenureYears] = useState("15");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loanName.trim() || !principalAmount.trim() || !interestRate.trim() || !tenureYears.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const cleanPrincipal = principalAmount.trim();
      if (!/^\d+(\.\d{1,2})?$/.test(cleanPrincipal) || cleanPrincipal === "0" || cleanPrincipal === "0.00") {
        throw new Error("Principal must be a positive number with up to 2 decimal places");
      }
      const pParts = cleanPrincipal.split(".");
      const formattedPrincipal = `${pParts[0]}.${(pParts[1] || "").padEnd(2, "0")}`;

      const cleanRate = interestRate.trim();
      if (!/^\d+(\.\d{1,2})?$/.test(cleanRate)) {
        throw new Error("Interest rate must be a valid number with up to 2 decimal places");
      }
      const rParts = cleanRate.split(".");
      const rateWhole = parseInt(rParts[0], 10);
      if (rateWhole < 0 || rateWhole > 50) {
        throw new Error("Interest rate must be between 0% and 50%");
      }
      const formattedRate = `${rParts[0]}.${(rParts[1] || "").padEnd(2, "0")}`;

      const cleanYears = tenureYears.trim();
      if (!/^\d+(\.\d+)?$/.test(cleanYears)) {
        throw new Error("Tenure years must be a positive number");
      }
      const yParts = cleanYears.split(".");
      const wholeYears = parseInt(yParts[0], 10);
      const fracMonths = yParts[1] ? Math.round(Number(`0.${yParts[1]}`) * 12) : 0;
      const tenureMonths = wholeYears * 12 + fracMonths;

      if (tenureMonths <= 0 || tenureMonths > 600) {
        throw new Error("Tenure must be between 1 month and 50 years (600 months)");
      }

      await api.loans.create({
        loan_name: loanName.trim(),
        principal_amount: formattedPrincipal,
        interest_rate: formattedRate,
        tenure_months: tenureMonths,
        start_date: startDate,
      });

      onSuccess();
      onClose();
      setLoanName("");
      setPrincipalAmount("");
      setInterestRate("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to record loan.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-stone-900/60 backdrop-blur-xs animate-fade-in p-0 sm:p-4">
      <div className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 border border-stone-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-2 border-b border-stone-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-stone-900 text-white flex items-center justify-center font-bold">
              <Building className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-stone-900">
                Record Liability
              </h3>
              <p className="text-[10px] text-stone-500">
                100% Private Vault • Never Visible in Family Space
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-500 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-3 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded-xl">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-stone-700 mb-1">
              Loan Title / Bank *
            </label>
            <input
              type="text"
              required
              value={loanName}
              onChange={(e) => setLoanName(e.target.value)}
              placeholder="e.g. HDFC Home Loan, SBI Auto Loan"
              className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-500/20 focus:border-stone-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Outstanding Principal (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                min="1000"
                required
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(e.target.value)}
                placeholder="4300000"
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-500/20 focus:border-stone-700 font-mono"
              />
            </div>
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Interest Rate (% p.a.) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.1"
                max="50"
                required
                value={interestRate}
                onChange={(e) => setInterestRate(e.target.value)}
                placeholder="8.50"
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-500/20 focus:border-stone-700 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Remaining Tenure (Years) *
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="50"
                required
                value={tenureYears}
                onChange={(e) => setTenureYears(e.target.value)}
                placeholder="15"
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-500/20 focus:border-stone-700"
              />
            </div>
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Start / Sanction Date *
              </label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-500/20 focus:border-stone-700"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-stone-900 hover:bg-black text-white font-bold rounded-xl shadow-xs transition active:scale-[0.99] disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Locking in Vault...</span>
                </>
              ) : (
                <span>Add Private Liability</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
