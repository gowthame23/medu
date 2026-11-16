'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Zap,
  CheckCircle2,
  ShieldCheck,
  ExternalLink,
  Loader2,
  Lock,
  Smartphone,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { UpcomingRadarRecord } from '@/lib/dataStore';

interface UPIIntentModalProps {
  bill: UpcomingRadarRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onPaymentReconciled: () => void;
  currentUserName?: string;
  currentUserId?: string;
}

export default function UPIIntentModal({
  bill,
  isOpen,
  onClose,
  onPaymentReconciled,
  currentUserName = 'Gowtham Ejjurothu',
  currentUserId = 'user-gowtham',
}: UPIIntentModalProps) {
  const [upiIntentData, setUpiIntentData] = useState<{
    upiUri: string;
    transactionRef: string;
    payeeVPA: string;
  } | null>(null);

  const [isReconciling, setIsReconciling] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [activeApp, setActiveApp] = useState<'gpay' | 'phonepe' | 'paytm' | 'generic'>('gpay');

  // Fetch standard NPCI UPI Intent URI upon modal open
  useEffect(() => {
    if (!bill || !isOpen) return;

    fetch('/api/radar/upi-intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ radarId: bill.id, payerUserId: currentUserId }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.upiUri) {
          setUpiIntentData(data);
        }
      })
      .catch(err => console.error('Error getting UPI intent:', err));
  }, [bill, isOpen, currentUserId]);

  if (!isOpen || !bill) return null;

  // Automated UPI Settlement Reconciliation
  const handleReconcilePayment = async (selectedMethod: string = 'Google Pay (UPI)') => {
    setIsReconciling(true);

    try {
      const txnRef = upiIntentData?.transactionRef || `UPI-${Math.floor(100000 + Math.random() * 900000)}`;

      const res = await fetch('/api/radar/reconcile-upi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          radarId: bill.id,
          payerUserId: currentUserId,
          payerName: currentUserName,
          paymentRef: txnRef,
          paymentMethod: selectedMethod,
        }),
      });

      if (res.ok) {
        setIsSuccess(true);
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.75 },
          colors: ['#059669', '#10b981', '#34d399', '#6ee7b7'],
        });

        setTimeout(() => {
          onPaymentReconciled();
          onClose();
          setIsSuccess(false);
          setIsReconciling(false);
        }, 1300);
      }
    } catch (err) {
      console.error('Reconciliation error:', err);
      setIsReconciling(false);
    }
  };

  const handleOpenAppAndReconcile = (app: 'gpay' | 'phonepe' | 'paytm' | 'generic') => {
    setActiveApp(app);
    const appName =
      app === 'gpay'
        ? 'Google Pay (UPI)'
        : app === 'phonepe'
        ? 'PhonePe (UPI)'
        : app === 'paytm'
        ? 'Paytm (UPI)'
        : 'UPI App';

    if (upiIntentData?.upiUri) {
      // Trigger native intent on mobile device
      window.location.href = upiIntentData.upiUri;
    }

    // Automatically reconcile payment state so user never has to manually mark paid!
    setTimeout(() => {
      handleReconcilePayment(appName);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="flex-1" onClick={onClose} />

      <div className="w-full max-w-md mx-auto bg-white rounded-t-3xl shadow-2xl border-t border-stone-200 p-5 space-y-4 max-h-[92vh] overflow-y-auto pb-safe">
        {/* Header */}
        <div className="flex flex-col items-center">
          <div className="w-10 h-1 rounded-full bg-stone-300 mb-3" />
          <div className="w-full flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
                <Zap className="w-4 h-4 text-emerald-700" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-stone-900 leading-none">
                  1-Tap UPI Intent Settlement
                </h3>
                <span className="text-[10px] text-stone-500">
                  Auto-reconciles &amp; attributes to {currentUserName}
                </span>
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
              {bill.consumerNumber || 'BBPS Verified Utility Biller'}
            </div>
            <div className="text-[9px] text-emerald-800 font-semibold mt-1 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-700" />
              <span>VPA: mend.bbps@yesbank</span>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[10px] text-stone-400 font-medium block">Amount Due</span>
            <div className="text-2xl font-black text-stone-900">
              ₹{bill.amount.toLocaleString('en-IN')}
            </div>
          </div>
        </div>

        {/* Success Feedback */}
        {isSuccess ? (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-1 animate-fade-in">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <div className="text-sm font-extrabold text-emerald-950">
              UPI Payment Reconciled &amp; Settled!
            </div>
            <p className="text-[11px] text-emerald-800">
              Attributed to <span className="font-bold">{currentUserName}</span> • Ref:{' '}
              <span className="font-mono font-bold">{upiIntentData?.transactionRef}</span>
            </p>
          </div>
        ) : (
          <div className="space-y-3 pt-1">
            <label className="block text-[11px] font-bold text-stone-700">
              Select UPI App (Opens Native App via Intent):
            </label>

            {/* UPI App Intent Buttons */}
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleOpenAppAndReconcile('gpay')}
                disabled={isReconciling}
                className="p-3 rounded-2xl border border-stone-200 bg-white hover:border-emerald-600 active:scale-95 transition-all text-center flex flex-col items-center justify-center gap-1 shadow-2xs"
              >
                <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-black text-xs shadow-xs">
                  G
                </div>
                <span className="text-xs font-bold text-stone-900 mt-0.5">Google Pay</span>
                <span className="text-[9px] text-stone-500">1-Tap Intent</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenAppAndReconcile('phonepe')}
                disabled={isReconciling}
                className="p-3 rounded-2xl border border-stone-200 bg-white hover:border-purple-600 active:scale-95 transition-all text-center flex flex-col items-center justify-center gap-1 shadow-2xs"
              >
                <div className="w-8 h-8 rounded-full bg-purple-700 text-white flex items-center justify-center font-black text-xs shadow-xs">
                  पे
                </div>
                <span className="text-xs font-bold text-stone-900 mt-0.5">PhonePe</span>
                <span className="text-[9px] text-stone-500">1-Tap Intent</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenAppAndReconcile('paytm')}
                disabled={isReconciling}
                className="p-3 rounded-2xl border border-stone-200 bg-white hover:border-sky-600 active:scale-95 transition-all text-center flex flex-col items-center justify-center gap-1 shadow-2xs"
              >
                <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center font-black text-xs shadow-xs">
                  P
                </div>
                <span className="text-xs font-bold text-stone-900 mt-0.5">Paytm</span>
                <span className="text-[9px] text-stone-500">1-Tap Intent</span>
              </button>
            </div>

            {/* Direct UPI Deep Link Trigger */}
            <div className="pt-1">
              <button
                onClick={() => handleOpenAppAndReconcile('generic')}
                disabled={isReconciling}
                className="w-full py-3 rounded-2xl text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
              >
                {isReconciling ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-200" />
                    <span>Reconciling UPI Intent Settlement...</span>
                  </>
                ) : (
                  <>
                    <Smartphone className="w-4 h-4 text-emerald-200" />
                    <span>Pay ₹{bill.amount.toLocaleString('en-IN')} via Native UPI Deep-Link</span>
                  </>
                )}
              </button>
            </div>

            {/* Deep-link Intent Spec details (Informative, reassuring) */}
            <div className="p-2.5 rounded-xl bg-stone-50 border border-stone-200 text-[10px] text-stone-500 flex items-center justify-between">
              <span className="font-mono truncate max-w-[280px]">
                {upiIntentData?.upiUri ? `Intent: ${upiIntentData.upiUri}` : 'Generating NPCI URI...'}
              </span>
              <span className="text-emerald-800 font-bold shrink-0">Auto-Reconciling</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
