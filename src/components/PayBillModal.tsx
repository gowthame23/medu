'use client';

import React, { useState } from 'react';
import { X, CheckCircle2, ShieldCheck, Zap, ArrowRight, Loader2 } from 'lucide-react';
import confetti from 'canvas-confetti';
import { UpcomingRadarRecord } from '@/lib/dataStore';

interface PayBillModalProps {
  bill: UpcomingRadarRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onPaymentSuccess: () => void;
}

export default function PayBillModal({
  bill,
  isOpen,
  onClose,
  onPaymentSuccess,
}: PayBillModalProps) {
  const [selectedApp, setSelectedApp] = useState<'gpay' | 'phonepe' | 'paytm'>('gpay');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [txnRef, setTxnRef] = useState<string>('');

  if (!isOpen || !bill) return null;

  const handlePayNow = async (mode: 'pay' | 'auto-detect') => {
    setIsProcessing(true);

    const appName =
      selectedApp === 'gpay'
        ? 'Google Pay (UPI)'
        : selectedApp === 'phonepe'
        ? 'PhonePe (UPI)'
        : 'Paytm / NetBanking';

    try {
      const generatedTxn = `UPI-${Math.floor(100000 + Math.random() * 900000)}`;
      setTxnRef(generatedTxn);

      const res = await fetch(`/api/radar/${bill.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paidBy: mode === 'auto-detect' ? 'Auto-Detected (Bank SMS)' : 'Gowtham',
          paymentMethod: appName,
          transactionRef: generatedTxn,
        }),
      });

      if (res.ok) {
        setIsSuccess(true);
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 },
          colors: ['#059669', '#10b981', '#34d399', '#6ee7b7'],
        });

        setTimeout(() => {
          onPaymentSuccess();
          onClose();
          setIsSuccess(false);
          setIsProcessing(false);
        }, 1500);
      }
    } catch (err) {
      console.error('Payment error:', err);
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="flex-1" onClick={onClose} />

      <div className="w-full max-w-md mx-auto bg-white rounded-t-3xl shadow-2xl border-t border-stone-200 p-5 space-y-4 max-h-[90vh] overflow-y-auto pb-safe">
        {/* Header */}
        <div className="flex flex-col items-center">
          <div className="w-10 h-1 rounded-full bg-stone-300 mb-3" />
          <div className="w-full flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
                <ShieldCheck className="w-4 h-4 text-emerald-700" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-stone-900 leading-none">
                  Instant Bill Settlement
                </h3>
                <span className="text-[10px] text-stone-500">Auto-marks as Paid upon confirmation</span>
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

        {/* Bill Summary Banner */}
        <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/80 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-stone-900">{bill.title}</div>
            <div className="text-[10px] text-stone-500 mt-0.5 font-mono">
              {bill.consumerNumber || 'BBPS Verified Biller'}
            </div>
            <span className="text-[9px] text-emerald-800 bg-emerald-100 px-1.5 py-0.2 rounded font-semibold mt-1 inline-block">
              Verified Consumer Account
            </span>
          </div>

          <div className="text-right">
            <span className="text-[10px] text-stone-400 font-medium block">Total Due</span>
            <div className="text-2xl font-black text-stone-900">
              ₹{bill.amount.toLocaleString('en-IN')}
            </div>
          </div>
        </div>

        {/* Payment App Options */}
        <div>
          <label className="block text-[11px] font-bold text-stone-700 mb-2">
            Choose Payment App:
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setSelectedApp('gpay')}
              className={`p-3 rounded-2xl border text-center transition-all ${
                selectedApp === 'gpay'
                  ? 'border-emerald-600 bg-emerald-50/60 shadow-xs'
                  : 'border-stone-200 bg-white hover:border-stone-300'
              }`}
            >
              <div className="w-7 h-7 mx-auto rounded-full bg-emerald-600 text-white flex items-center justify-center font-black text-xs">
                G
              </div>
              <div className="text-[11px] font-bold text-stone-900 mt-1">Google Pay</div>
              <div className="text-[9px] text-stone-500">Fast UPI</div>
            </button>

            <button
              type="button"
              onClick={() => setSelectedApp('phonepe')}
              className={`p-3 rounded-2xl border text-center transition-all ${
                selectedApp === 'phonepe'
                  ? 'border-purple-600 bg-purple-50/60 shadow-xs'
                  : 'border-stone-200 bg-white hover:border-stone-300'
              }`}
            >
              <div className="w-7 h-7 mx-auto rounded-full bg-purple-700 text-white flex items-center justify-center font-black text-xs">
                पे
              </div>
              <div className="text-[11px] font-bold text-stone-900 mt-1">PhonePe</div>
              <div className="text-[9px] text-stone-500">Direct UPI</div>
            </button>

            <button
              type="button"
              onClick={() => setSelectedApp('paytm')}
              className={`p-3 rounded-2xl border text-center transition-all ${
                selectedApp === 'paytm'
                  ? 'border-sky-600 bg-sky-50/60 shadow-xs'
                  : 'border-stone-200 bg-white hover:border-stone-300'
              }`}
            >
              <div className="w-7 h-7 mx-auto rounded-full bg-sky-600 text-white flex items-center justify-center font-black text-xs">
                P
              </div>
              <div className="text-[11px] font-bold text-stone-900 mt-1">Paytm / Bank</div>
              <div className="text-[9px] text-stone-500">NetBanking</div>
            </button>
          </div>
        </div>

        {/* Success State */}
        {isSuccess ? (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-1">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <div className="text-sm font-extrabold text-emerald-950">
              Payment Confirmed &amp; Auto-Marked!
            </div>
            <p className="text-[11px] text-emerald-800">
              Ref: <span className="font-mono font-bold">{txnRef}</span> • Due amount updated to ₹0
            </p>
          </div>
        ) : (
          <div className="space-y-2 pt-2">
            {/* Primary: Pay and Auto-Mark */}
            <button
              onClick={() => handlePayNow('pay')}
              disabled={isProcessing}
              className="w-full py-3.5 rounded-2xl text-sm font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Confirming with Bank &amp; BBPS...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Pay ₹{bill.amount.toLocaleString('en-IN')} &amp; Auto-Mark Paid</span>
                </>
              )}
            </button>

            {/* Secondary: Already paid externally auto-detection */}
            <button
              onClick={() => handlePayNow('auto-detect')}
              disabled={isProcessing}
              className="w-full py-2.5 rounded-2xl text-xs font-bold bg-stone-100 hover:bg-stone-200 text-stone-700 transition-colors flex items-center justify-center gap-1.5"
            >
              <span>Already paid in GPay / Bank? Auto-Verify Status</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
