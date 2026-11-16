'use client';

import React, { useState, useEffect } from 'react';
import { X, Calendar, PlusCircle } from 'lucide-react';

interface AddRadarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userId?: string;
}

export default function AddRadarModal({ isOpen, onClose, onSuccess, userId }: AddRadarModalProps) {
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [recurringType, setRecurringType] = useState<'NONE' | 'MONTHLY' | 'YEARLY'>('MONTHLY');
  const [category, setCategory] = useState('Utilities');
  const [assignedTo, setAssignedTo] = useState<'Gowtham' | 'Priya' | 'Shared'>('Gowtham');
  const [consumerNumber, setConsumerNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split('T')[0];
    setDueDate(tomorrowStr);
  }, []);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !amount) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/radar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: assignedTo === 'Shared' ? undefined : userId,
          title: title.trim(),
          amount: parseFloat(amount),
          dueDate: new Date(dueDate).toISOString(),
          recurringType,
          category,
          assignedTo,
          consumerNumber: consumerNumber.trim() || undefined,
        }),
      });

      if (res.ok) {
        onSuccess();
        onClose();
        setTitle('');
        setAmount('');
        setConsumerNumber('');
      }
    } catch (err) {
      console.error('Error adding radar reminder:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-xs">
      <div className="relative w-full max-w-md bg-white rounded-3xl shadow-xl border border-stone-200/80 overflow-hidden">
        <div className="px-6 pt-6 pb-4 border-b border-stone-100 flex items-center justify-between bg-stone-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-emerald-700" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900">Add to Upcoming Radar</h2>
              <p className="text-xs text-stone-500">Proactively track next bills without surprise stress</p>
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
              Bill / Payment Title
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Wi-Fi Bill, Water Bill, Car EMI"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Amount (₹)
              </label>
              <input
                type="number"
                required
                min="1"
                step="any"
                placeholder="₹1,250"
                value={amount}
                onChange={e => setAmount(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Due Date
              </label>
              <input
                type="date"
                required
                value={dueDate}
                onChange={e => setDueDate(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Recurrence
              </label>
              <select
                value={recurringType}
                onChange={e => setRecurringType(e.target.value as 'NONE' | 'MONTHLY' | 'YEARLY')}
                className="w-full px-3 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700 bg-white"
              >
                <option value="NONE">One-time payment</option>
                <option value="MONTHLY">Monthly recurring</option>
                <option value="YEARLY">Yearly recurring</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700 bg-white"
              >
                <option value="Utilities">Utilities & Bills</option>
                <option value="Housing">Housing & Rent</option>
                <option value="Subscriptions">Subscriptions</option>
                <option value="Loan EMI">Loan EMI</option>
                <option value="Insurance">Insurance & Health</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Assigned To
              </label>
              <select
                value={assignedTo}
                onChange={e => setAssignedTo(e.target.value as 'Gowtham' | 'Priya' | 'Shared')}
                className="w-full px-3 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700 bg-white font-medium text-stone-800"
              >
                <option value="Gowtham">You (Gowtham)</option>
                <option value="Priya">Priya (Partner)</option>
                <option value="Shared">Shared Household</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Consumer / Account # (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. BESCOM-CA #4928120"
                value={consumerNumber}
                onChange={e => setConsumerNumber(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2">
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
              className="px-5 py-2.5 text-xs font-medium rounded-xl bg-emerald-800 text-white hover:bg-emerald-900 transition-all flex items-center gap-1.5 shadow-xs"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Adding...' : 'Add to Radar'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
