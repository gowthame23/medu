'use client';

import React, { useState } from 'react';
import { X, CheckCircle, Sparkles, Moon, Plus, Undo2 } from 'lucide-react';
import confetti from 'canvas-confetti';

interface NightlyCheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userId?: string;
  userName?: string;
}

interface CategoryConfig {
  key: string;
  label: string;
  icon: string;
  defaultQuickStep: number;
}

const CATEGORIES: CategoryConfig[] = [
  { key: 'groceries', label: 'Groceries', icon: '🛒', defaultQuickStep: 200 },
  { key: 'bills', label: 'Bills', icon: '💡', defaultQuickStep: 500 },
  { key: 'transport', label: 'Transport', icon: '🚇', defaultQuickStep: 100 },
  { key: 'dining', label: 'Dining', icon: '🍲', defaultQuickStep: 300 },
  { key: 'health', label: 'Health', icon: '💊', defaultQuickStep: 200 },
  { key: 'misc', label: 'Misc', icon: '✨', defaultQuickStep: 150 },
];

export default function NightlyCheckInModal({
  isOpen,
  onClose,
  onSuccess,
  userId,
  userName = 'You',
}: NightlyCheckInModalProps) {
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [activeCategory, setActiveCategory] = useState<string>('groceries');
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [hasCelebrated, setHasCelebrated] = useState<boolean>(false);

  if (!isOpen) return null;

  const totalSpent = Object.values(categories).reduce((sum, val) => sum + (val || 0), 0);

  const handleAddAmount = (catKey: string, amount: number) => {
    setCategories(prev => ({
      ...prev,
      [catKey]: (prev[catKey] || 0) + amount,
    }));
  };

  const handleResetCategory = (catKey: string) => {
    setCategories(prev => {
      const next = { ...prev };
      delete next[catKey];
      return next;
    });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/daily-logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId,
          totalSpent,
          categoriesBreakdown: categories,
          notes: notes.trim(),
        }),
      });

      if (res.ok) {
        setHasCelebrated(true);
        setTimeout(() => {
          onSuccess();
          onClose();
          setHasCelebrated(false);
          setCategories({});
          setNotes('');
        }, 800);
      }
    } catch (err) {
      console.error('Failed to submit check-in:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/50 backdrop-blur-xs animate-fade-in">
      {/* Background touch dismiss */}
      <div className="flex-1" onClick={onClose} />

      {/* Mobile Bottom Sheet Container */}
      <div className="w-full max-w-md mx-auto bg-white rounded-t-3xl shadow-2xl border-t border-stone-200/80 p-5 space-y-4 max-h-[90vh] overflow-y-auto pb-safe">
        {/* Drag Pill & Header */}
        <div className="flex flex-col items-center">
          <div className="w-10 h-1 rounded-full bg-stone-300 mb-3" />
          <div className="w-full flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
                <Moon className="w-4 h-4 text-emerald-700" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-stone-900 leading-none">
                  30s Nightly Check-In
                </h3>
                <span className="text-[10px] text-stone-500">Tap chips to add today’s total</span>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-stone-100 text-stone-500 flex items-center justify-center active:scale-95"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Total Big Pill */}
        <div className="p-3.5 rounded-2xl bg-emerald-50/80 border border-emerald-100 text-center">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">
            Today&apos;s Total
          </span>
          <div className="text-3xl font-black text-stone-900 mt-0.5">
            ₹{totalSpent.toLocaleString('en-IN')}
          </div>
        </div>

        {/* Mobile Quick-Chips Matrix (Thumb-Tappable) */}
        <div>
          <label className="block text-[11px] font-bold text-stone-700 mb-1.5">
            Tap Category to Add:
          </label>
          <div className="grid grid-cols-3 gap-2">
            {CATEGORIES.map(cat => {
              const currentVal = categories[cat.key] || 0;
              const isSelected = activeCategory === cat.key;
              return (
                <button
                  key={cat.key}
                  type="button"
                  onClick={() => {
                    setActiveCategory(cat.key);
                    handleAddAmount(cat.key, cat.defaultQuickStep);
                  }}
                  className={`p-2.5 rounded-2xl border text-center transition-all flex flex-col items-center justify-between min-h-[70px] active:scale-95 ${
                    isSelected
                      ? 'border-emerald-600 bg-emerald-50/60 shadow-xs'
                      : 'border-stone-200 bg-white hover:border-stone-300'
                  }`}
                >
                  <span className="text-xl">{cat.icon}</span>
                  <span className="text-[10px] font-bold text-stone-800 mt-1 block">
                    {cat.label}
                  </span>
                  <span className="text-[10px] font-extrabold text-emerald-800">
                    {currentVal > 0 ? `₹${currentVal}` : `+₹${cat.defaultQuickStep}`}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Adjust Step Increments for Active Category */}
        <div className="p-3 rounded-2xl bg-stone-100/70 border border-stone-200/60 space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-stone-700">
              Quick adjust for <span className="text-emerald-800 capitalize font-bold">{activeCategory}</span>:
            </span>
            {(categories[activeCategory] || 0) > 0 && (
              <button
                type="button"
                onClick={() => handleResetCategory(activeCategory)}
                className="text-stone-400 hover:text-stone-700 flex items-center gap-1 text-[10px]"
              >
                <Undo2 className="w-3 h-3" /> Clear
              </button>
            )}
          </div>

          <div className="grid grid-cols-4 gap-1.5">
            {[100, 250, 500, 1000].map(step => (
              <button
                key={step}
                type="button"
                onClick={() => handleAddAmount(activeCategory, step)}
                className="py-1.5 text-xs font-bold rounded-xl bg-white border border-stone-200 text-stone-800 active:scale-95 transition-transform"
              >
                +₹{step}
              </button>
            ))}
          </div>
        </div>

        {/* Optional Note */}
        <div>
          <input
            type="text"
            placeholder="Quick note (optional, e.g. groceries & train)"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 bg-white focus:outline-none focus:ring-1 focus:ring-emerald-700"
          />
        </div>

        {/* Giant Mobile Bottom Action Button */}
        <div className="pt-2">
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || hasCelebrated}
            className="w-full py-3.5 rounded-2xl text-sm font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
          >
            {hasCelebrated ? (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-300" />
                <span>Saved for today ✨</span>
              </>
            ) : (
              <>
                <span>{isSubmitting ? 'Saving...' : 'Save Daily Check-In'}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
