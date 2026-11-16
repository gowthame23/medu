"use client";

import React, { useState, useEffect } from "react";
import {
  Building,
  Lock,
  Unlock,
  Plus,
  Loader2,
  Trash2,
  Sliders,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  api,
  LoanItem,
  DailyCostResponse,
  PrepaymentSimulationResponse,
} from "@/lib/api";

interface LiabilitiesVaultViewProps {
  loans: LoanItem[];
  onOpenAddLoan: () => void;
  onRefreshLoans: () => void;
  userName?: string;
}

function computeCoffeeEquiv(dailyInterestStr: string): string {
  const parts = dailyInterestStr.split(".");
  const rupees = parseInt(parts[0], 10) || 0;
  const paise = parts[1] ? (parseInt(parts[1].slice(0, 2).padEnd(2, "0"), 10) || 0) : 0;
  const totalPaise = rupees * 100 + paise;
  // 1 coffee = 250 rupees = 25,000 paise
  const tenths = Math.round((totalPaise * 10) / 25000);
  return (tenths / 10).toFixed(1);
}

export default function LiabilitiesVaultView({
  loans,
  onOpenAddLoan,
  onRefreshLoans,
  userName = "You",
}: LiabilitiesVaultViewProps) {
  const [selectedLoanId, setSelectedLoanId] = useState<string>("");
  const [dailyCost, setDailyCost] = useState<DailyCostResponse | null>(null);
  const [prepaymentInput, setPrepaymentInput] = useState<string>("50000");
  const [simulation, setSimulation] = useState<PrepaymentSimulationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isVaultLocked, setIsVaultLocked] = useState<boolean>(false);
  const [showCoffeeEquiv, setShowCoffeeEquiv] = useState<boolean>(false);

  const activeLoanId = selectedLoanId && loans.some((l) => l.id === selectedLoanId)
    ? selectedLoanId
    : loans[0]?.id || "";

  useEffect(() => {
    if (!activeLoanId) {
      return;
    }

    let isMounted = true;

    async function loadLoanDetails() {
      try {
        setIsLoading(true);
        const [costData, simData] = await Promise.all([
          api.loans.getDailyCost(activeLoanId),
          api.loans.simulatePrepayment(activeLoanId, {
            prepayment_amount: prepaymentInput || "0",
            prepayment_month: 1,
          }),
        ]);
        if (isMounted) {
          setDailyCost(costData);
          setSimulation(simData);
        }
      } catch (err) {
        console.error("Error loading loan details:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadLoanDetails();

    return () => {
      isMounted = false;
    };
  }, [activeLoanId, prepaymentInput]);

  const handleDeleteLoan = async (loanId: string) => {
    if (!confirm("Are you sure you want to remove this loan from your private vault?")) return;
    try {
      await api.loans.delete(loanId);
      onRefreshLoans();
    } catch (err) {
      console.error("Failed to delete loan:", err);
    }
  };

  const selectedLoan = loans.find((l) => l.id === activeLoanId);

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
            className="text-[10px] px-2.5 py-1 rounded-xl bg-stone-800 hover:bg-stone-700 text-stone-300 font-medium transition"
          >
            {isVaultLocked ? "Unlock" : "Lock"}
          </button>
        </div>
      </div>

      {isVaultLocked ? (
        <div className="p-8 text-center bg-white rounded-3xl border border-stone-200/80 space-y-3">
          <Lock className="w-8 h-8 text-stone-400 mx-auto" />
          <p className="text-xs font-semibold text-stone-700">Vault is locked for privacy</p>
          <button
            onClick={() => setIsVaultLocked(false)}
            className="px-4 py-2 bg-stone-900 text-white text-xs font-bold rounded-xl"
          >
            Unlock Private Data
          </button>
        </div>
      ) : loans.length === 0 ? (
        <div className="p-8 text-center bg-white rounded-3xl border border-stone-200/80 space-y-3">
          <Building className="w-8 h-8 text-stone-300 mx-auto" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-stone-800">No liabilities recorded yet</h4>
            <p className="text-[11px] text-stone-500 max-w-xs mx-auto">
              Track home loans, car loans, or credit lines with exact daily interest and prepayment simulations.
            </p>
          </div>
          <button
            onClick={onOpenAddLoan}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-800 text-white rounded-xl text-xs font-bold shadow-xs hover:bg-emerald-900 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add First Loan</span>
          </button>
        </div>
      ) : (
        <>
          {/* Loan Selector Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {loans.map((loan) => (
              <button
                key={loan.id}
                onClick={() => setSelectedLoanId(loan.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition ${
                  activeLoanId === loan.id
                    ? "bg-emerald-800 text-white shadow-xs"
                    : "bg-white text-stone-600 border border-stone-200/80 hover:bg-stone-50"
                }`}
              >
                {loan.loan_name}
              </button>
            ))}
            <button
              onClick={onOpenAddLoan}
              className="p-1.5 rounded-xl border border-dashed border-stone-300 text-stone-500 hover:text-stone-900 hover:border-stone-400 transition"
              title="Add another liability"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Daily Cost Card */}
          {dailyCost && selectedLoan && (
            <div className="p-5 rounded-3xl bg-white border border-stone-200/80 shadow-xs space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">
                    Daily Interest Burden
                  </span>
                  <div className="flex items-baseline gap-1.5 mt-0.5">
                    <span className="text-3xl font-black text-stone-900 font-mono">
                      ₹{dailyCost.daily_interest}
                    </span>
                    <span className="text-xs font-semibold text-stone-500">/ day</span>
                  </div>
                  <div className="text-[11px] text-stone-500 mt-1 font-mono">
                    ₹{dailyCost.monthly_interest_approx} monthly interest • {selectedLoan.interest_rate}% p.a.
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteLoan(selectedLoan.id)}
                  className="p-2 text-stone-400 hover:text-rose-600 rounded-xl transition"
                  title="Delete loan"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Coffee Equiv Toggle (Hidden by default) */}
              <div className="border-t border-stone-100 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCoffeeEquiv(!showCoffeeEquiv)}
                  className="flex items-center gap-1.5 text-[11px] font-semibold text-stone-500 hover:text-stone-700 transition"
                >
                  <span>Alternative Framing Equivalent</span>
                  {showCoffeeEquiv ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showCoffeeEquiv && (
                  <p className="mt-1.5 text-xs text-stone-600 bg-stone-50 p-2.5 rounded-xl border border-stone-200/60">
                    Equivalent to about{" "}
                    <span className="font-bold text-stone-900 font-mono">
                      {computeCoffeeEquiv(dailyCost.daily_interest)}
                    </span>{" "}
                    artisan coffees per day in pure interest.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Prepayment Simulator */}
          <div className="p-5 rounded-3xl bg-white border border-stone-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-800" />
              <h4 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
                Prepayment Simulator
              </h4>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Lump Sum Prepayment Amount (₹)
              </label>
              <input
                type="number"
                step="5000"
                min="1000"
                value={prepaymentInput}
                onChange={(e) => setPrepaymentInput(e.target.value)}
                placeholder="50000"
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>

            {isLoading ? (
              <div className="py-6 flex justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-stone-400" />
              </div>
            ) : simulation ? (
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <div className="p-3 bg-emerald-50 rounded-2xl border border-emerald-200/70">
                  <div className="text-[10px] font-bold text-emerald-800 uppercase">
                    Interest Saved
                  </div>
                  <div className="text-lg font-black text-emerald-950 font-mono mt-0.5">
                    ₹{simulation.total_interest_saved}
                  </div>
                  <div className="text-[10px] text-emerald-700 mt-0.5">
                    pure wealth preserved
                  </div>
                </div>

                <div className="p-3 bg-stone-50 rounded-2xl border border-stone-200/70">
                  <div className="text-[10px] font-bold text-stone-600 uppercase">
                    Tenure Reduced
                  </div>
                  <div className="text-lg font-black text-stone-900 font-mono mt-0.5">
                    {simulation.months_saved} mos
                  </div>
                  <div className="text-[10px] text-stone-500 mt-0.5">
                    faster debt freedom
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
