"use client";

import React, { useState } from "react";
import { X, PlusCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface AddRadarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  currentMode: "individual" | "family";
  familyId?: string;
}

export default function AddRadarModal({
  isOpen,
  onClose,
  onSuccess,
  currentMode,
  familyId,
}: AddRadarModalProps) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState(() => new Date(Date.now() + 86400000).toISOString().split("T")[0]);
  const [recurrenceInterval, setRecurrenceInterval] = useState<"NONE" | "MONTHLY" | "YEARLY">("MONTHLY");
  const [category, setCategory] = useState("utility");
  const [consumerNumber, setConsumerNumber] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !amount.trim() || !dueDate) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const cleanAmount = amount.trim();
      if (!/^\d+(\.\d{1,2})?$/.test(cleanAmount) || cleanAmount === "0" || cleanAmount === "0.00") {
        throw new Error("Please enter a valid positive bill amount with up to 2 decimal places");
      }
      const aParts = cleanAmount.split(".");
      const formattedAmount = `${aParts[0]}.${(aParts[1] || "").padEnd(2, "0")}`;

      if (currentMode === "family" && familyId) {
        await api.families.createBill(familyId, {
          title: title.trim(),
          amount: formattedAmount,
          due_date: dueDate,
          consumer_number: consumerNumber.trim() || undefined,
          category,
          recurrence_interval: recurrenceInterval,
        });
      } else {
        await api.bills.createPersonal({
          title: title.trim(),
          amount: formattedAmount,
          due_date: dueDate,
          consumer_number: consumerNumber.trim() || undefined,
          category,
          recurrence_interval: recurrenceInterval,
        });
      }

      onSuccess();
      onClose();
      setTitle("");
      setAmount("");
      setConsumerNumber("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add bill reminder.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-stone-900/60 backdrop-blur-xs animate-fade-in p-0 sm:p-4">
      <div className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 border border-stone-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-2 border-b border-stone-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
              <PlusCircle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-stone-900">
                Add Radar Reminder
              </h3>
              <p className="text-[10px] text-stone-500">
                {currentMode === "family" ? "Household Bill (Shared)" : "Personal Bill (100% Private)"}
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
              Bill Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Electricity BESCOM, WiFi Fiber"
              className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Amount (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="2450.00"
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700 font-mono"
              />
            </div>
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Due Date *
              </label>
              <input
                type="date"
                required
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700"
              >
                <option value="utility">Utility (Electricity/Water)</option>
                <option value="telecom">Broadband / Mobile</option>
                <option value="subscription">Subscription / Streaming</option>
                <option value="housing">Rent / Maintenance</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-stone-700 mb-1">
                Recurrence
              </label>
              <select
                value={recurrenceInterval}
                onChange={(e) => setRecurrenceInterval(e.target.value as "NONE" | "MONTHLY" | "YEARLY")}
                className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700"
              >
                <option value="MONTHLY">Monthly</option>
                <option value="NONE">One-time only</option>
                <option value="YEARLY">Yearly</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block font-semibold text-stone-700 mb-1">
              Consumer / Account # (Optional)
            </label>
            <input
              type="text"
              value={consumerNumber}
              onChange={(e) => setConsumerNumber(e.target.value)}
              placeholder="e.g. CA 4928120"
              className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700 font-mono text-xs"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-800 hover:bg-emerald-900 text-white font-bold rounded-xl shadow-xs transition active:scale-[0.99] disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Adding to Radar...</span>
                </>
              ) : (
                <span>Add to Tomorrow&apos;s Radar</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
