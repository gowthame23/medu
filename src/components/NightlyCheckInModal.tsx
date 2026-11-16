"use client";

import React, { useState, useEffect } from "react";
import { X, Moon, Loader2, Plus, Trash2 } from "lucide-react";
import { api, Category } from "@/lib/api";

interface NightlyCheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function parseMoneyToPaise(val: string): number | null {
  const trimmed = val.trim();
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return null;
  const parts = trimmed.split(".");
  const rupees = parseInt(parts[0], 10);
  const paise = parts[1] ? parseInt(parts[1].padEnd(2, "0"), 10) : 0;
  if (rupees === 0 && paise === 0) return null;
  return rupees * 100 + paise;
}

function formatPaiseToString(paise: number): string {
  const r = Math.floor(paise / 100);
  const p = paise % 100;
  return `${r}.${p.toString().padStart(2, "0")}`;
}

export default function NightlyCheckInModal({
  isOpen,
  onClose,
  onSuccess,
}: NightlyCheckInModalProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("");
  const [amount, setAmount] = useState<string>("");
  const [stagedEntries, setStagedEntries] = useState<Array<{ categoryId: string; categoryName: string; amount: string }>>([]);
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoadingCategories, setIsLoadingCategories] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;

    async function loadCategories() {
      try {
        setIsLoadingCategories(true);
        const cats = await api.categories.list();
        if (isMounted) {
          setCategories(cats);
          if (cats.length > 0) setSelectedCategoryId(cats[0].id);
        }
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : "Failed to load expense categories");
      } finally {
        if (isMounted) setIsLoadingCategories(false);
      }
    }

    loadCategories();

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleStageEntry = (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount.trim() || !selectedCategoryId) return;

    const paise = parseMoneyToPaise(amount);
    if (paise === null || paise <= 0) {
      setError("Please enter a valid expense amount");
      return;
    }

    const cat = categories.find((c) => c.id === selectedCategoryId);
    const catName = cat ? cat.name : "Expense";

    setStagedEntries((prev) => [
      ...prev,
      {
        categoryId: selectedCategoryId,
        categoryName: catName,
        amount: formatPaiseToString(paise),
      },
    ]);
    setAmount("");
    setError(null);
  };

  const handleRemoveStaged = (index: number) => {
    setStagedEntries((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    const todayStr = new Date().toISOString().split("T")[0];

    try {
      // Add each staged entry to today's daily log
      for (const entry of stagedEntries) {
        await api.dailyLogs.addEntry(todayStr, entry.categoryId, entry.amount);
      }

      // Update notes if provided
      if (notes.trim()) {
        await api.dailyLogs.updateNotes(todayStr, notes.trim());
      }

      onSuccess();
      onClose();
      setStagedEntries([]);
      setNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to complete check-in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalStaged = formatPaiseToString(
    stagedEntries.reduce((sum, item) => sum + (parseMoneyToPaise(item.amount) ?? 0), 0)
  );

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/50 backdrop-blur-xs animate-fade-in">
      <div className="flex-1" onClick={onClose} />

      <div className="w-full max-w-md mx-auto bg-white rounded-t-3xl shadow-2xl border-t border-stone-200/80 p-5 space-y-4 max-h-[90vh] overflow-y-auto pb-safe">
        <div className="flex items-center justify-between pb-2 border-b border-stone-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center font-bold">
              <Moon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-stone-900">
                Daily Financial Check-in
              </h3>
              <p className="text-[10px] text-stone-500">
                30-second low-friction ritual • No guilt, pure awareness
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

        {/* Add Entry Line */}
        <form onSubmit={handleStageEntry} className="space-y-2 text-xs">
          <div className="grid grid-cols-12 gap-2 items-end">
            <div className="col-span-6">
              <label className="block font-semibold text-stone-700 mb-1">
                Category
              </label>
              <select
                value={selectedCategoryId}
                onChange={(e) => setSelectedCategoryId(e.target.value)}
                disabled={isLoadingCategories}
                className="w-full px-2.5 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 text-xs"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-span-4">
              <label className="block font-semibold text-stone-700 mb-1">
                Amount (₹)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="250.00"
                className="w-full px-2.5 py-2 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 text-xs font-mono"
              />
            </div>

            <div className="col-span-2">
              <button
                type="submit"
                className="w-full py-2 bg-emerald-800 hover:bg-emerald-900 text-white rounded-xl flex items-center justify-center transition"
                title="Add expense"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </form>

        {/* Staged list */}
        {stagedEntries.length > 0 && (
          <div className="space-y-1.5 pt-2">
            <div className="text-[11px] font-bold text-stone-600 flex justify-between">
              <span>Expenses to Record</span>
              <span className="font-mono text-emerald-800">Total: ₹{totalStaged}</span>
            </div>
            <div className="space-y-1 max-h-36 overflow-y-auto">
              {stagedEntries.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-xl bg-stone-50 border border-stone-100 text-xs"
                >
                  <span className="font-medium text-stone-800">{item.categoryName}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-stone-900">₹{item.amount}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveStaged(idx)}
                      className="text-stone-400 hover:text-rose-600 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        <div>
          <label className="block text-xs font-semibold text-stone-700 mb-1">
            Day reflection (Optional)
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Spent intentionally today. No stress."
            className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-700 resize-none"
          />
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || (stagedEntries.length === 0 && !notes.trim())}
          className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-bold rounded-2xl shadow-xs transition active:scale-[0.99] disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Saving Check-in...</span>
            </>
          ) : (
            <span>Complete Check-In</span>
          )}
        </button>
      </div>
    </div>
  );
}
