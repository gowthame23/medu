"use client";

import React, { useState } from "react";
import { X, ShieldCheck, AlertTriangle, Loader2 } from "lucide-react";
import { api, BillRadarItem } from "@/lib/api";

interface SafeVerifyPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  bill: BillRadarItem | null;
  currentMode: "individual" | "family";
  familyId?: string;
  onSuccess: () => void;
}

export default function SafeVerifyPaymentModal({
  isOpen,
  onClose,
  bill,
  currentMode,
  familyId,
  onSuccess,
}: SafeVerifyPaymentModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !bill) return null;

  const handleMarkPaid = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      if (currentMode === "family" && familyId) {
        await api.families.markBillPaid(familyId, bill.id);
      } else {
        await api.bills.markPersonalPaid(bill.id);
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to mark bill as paid.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-stone-900/60 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4 animate-fade-in">
      <div className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 border border-stone-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-amber-100 text-amber-900 flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5 text-amber-800" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-stone-900 leading-tight">
                Self-Reported Payment
              </h3>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Marking paid without BBPS confirmation
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-500 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-3 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded-xl">
            {error}
          </div>
        )}

        <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200/80 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-stone-900">{bill.title}</div>
            <div className="text-[10px] text-stone-500">
              {bill.consumer_number_masked || "No account number"} • Due {bill.due_date}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-extrabold text-stone-900 font-mono">
              ₹{bill.amount}
            </div>
            <span className="text-[9px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
              Self-Reported
            </span>
          </div>
        </div>

        <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-2xl flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div className="text-[11px] text-amber-900 space-y-1">
            <p className="font-semibold">Important Payment Notice</p>
            <p className="text-amber-800">
              This marks the bill as <span className="font-bold underline">PAID_UNVERIFIED</span>. It records your display name so household members know who self-reported. If not settled at the biller or banking partner, service interruption could occur.
            </p>
          </div>
        </div>

        <div className="space-y-2 pt-2">
          <button
            onClick={handleMarkPaid}
            disabled={isSubmitting}
            className="w-full py-3 bg-amber-800 hover:bg-amber-900 text-white rounded-2xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-xs disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Recording Status...</span>
              </>
            ) : (
              <span>Confirm & Mark as Self-Reported</span>
            )}
          </button>

          <button
            onClick={onClose}
            className="w-full py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-2xl text-xs font-semibold transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
