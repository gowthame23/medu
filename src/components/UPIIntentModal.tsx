"use client";

import React, { useState } from "react";
import { X, Zap, Loader2, CheckCircle2 } from "lucide-react";
import { api, BillRadarItem } from "@/lib/api";

interface UPIIntentModalProps {
  bill: BillRadarItem | null;
  isOpen: boolean;
  onClose: () => void;
  onPaymentReconciled: () => void;
  currentMode: "individual" | "family";
  familyId?: string;
}

export default function UPIIntentModal({
  bill,
  isOpen,
  onClose,
  onPaymentReconciled,
  currentMode,
  familyId,
}: UPIIntentModalProps) {
  const [isPaying, setIsPaying] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [paymentRef, setPaymentRef] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey] = useState<string>(() => crypto.randomUUID());

  if (!isOpen || !bill) return null;

  const handlePay = async () => {
    setIsPaying(true);
    setError(null);

    try {
      let result;
      if (currentMode === "family" && familyId) {
        result = await api.families.payBill(familyId, bill.id, idempotencyKey);
      } else {
        result = await api.bills.payPersonal(bill.id, idempotencyKey);
      }

      setPaymentRef(result.payment_reference);
      setIsSuccess(true);

      setTimeout(() => {
        onPaymentReconciled();
        onClose();
        setIsSuccess(false);
        setIsPaying(false);
      }, 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Payment failed. Please retry.");
      setIsPaying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-stone-900/60 backdrop-blur-xs animate-fade-in p-0 sm:p-4">
      <div className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 border border-stone-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-2 border-b border-stone-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
              <Zap className="w-4 h-4 fill-emerald-800" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-sm font-extrabold text-stone-900">
                  UPI 1-Tap Payment
                </h3>
                <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded">
                  Sandbox Simulated
                </span>
              </div>
              <p className="text-[10px] text-stone-500">
                Idempotency Protected • Verified Settlement Provider
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

        <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-stone-900">{bill.title}</div>
            <div className="text-[11px] text-stone-500 font-mono mt-0.5">
              {bill.consumer_number_masked || "Direct Utility"}
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-black text-emerald-900 font-mono">
              ₹{bill.amount}
            </div>
            <div className="text-[10px] text-emerald-700 font-semibold">
              Due {bill.due_date}
            </div>
          </div>
        </div>

        {isSuccess ? (
          <div className="p-6 text-center space-y-2 bg-emerald-50 rounded-2xl border border-emerald-200">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <h4 className="text-sm font-bold text-emerald-900">Payment Verified & Settled</h4>
            <p className="text-xs text-stone-600 font-mono">Ref: {paymentRef}</p>
          </div>
        ) : (
          <div className="space-y-3 pt-1">
            <div className="text-[11px] text-stone-500 bg-stone-50 p-3 rounded-xl border border-stone-200/70">
              <span className="font-semibold text-stone-700">Sandbox Notice:</span> In v1, UPI payments execute via the simulated sandbox payment provider. The bill status updates to <span className="font-bold">PAID</span> upon provider confirmation with full attribution snapshot.
            </div>

            <button
              onClick={handlePay}
              disabled={isPaying}
              className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-800 hover:bg-emerald-900 text-white font-bold rounded-2xl shadow-xs transition active:scale-[0.99] disabled:opacity-50 text-xs"
            >
              {isPaying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying via Provider...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-white" />
                  <span>Execute Payment (₹{bill.amount})</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
