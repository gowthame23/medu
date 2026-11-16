'use client';

import React, { useState } from 'react';
import { X, ShieldCheck, AlertTriangle, RefreshCw, CheckCircle2, ArrowRight } from 'lucide-react';
import { UpcomingRadarRecord } from '@/lib/dataStore';

interface SafeVerifyPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  bill: UpcomingRadarRecord | null;
  activeUserName: string;
  onConfirmVerification: (
    billId: string,
    verificationType: 'BBPS_VERIFIED' | 'SELF_REPORTED',
    paymentMethod: string
  ) => Promise<void>;
}

export default function SafeVerifyPaymentModal({
  isOpen,
  onClose,
  bill,
  activeUserName,
  onConfirmVerification,
}: SafeVerifyPaymentModalProps) {
  const [selectedApp, setSelectedApp] = useState<string>('PhonePe');
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<{
    status: 'success' | 'warning' | null;
    message: string;
  }>({ status: null, message: '' });

  if (!isOpen || !bill) return null;

  // 1. Auto-Verify with BBPS / Biller Registry
  const handleAutoVerifyWithBBPS = async () => {
    setIsVerifying(true);
    setVerificationResult({ status: null, message: '' });

    // Simulate contacting electricity/broadband registry
    setTimeout(async () => {
      setIsVerifying(false);
      setVerificationResult({
        status: 'success',
        message: `Biller confirmed: ₹${bill.amount.toLocaleString('en-IN')} received for ${bill.consumerNumber || 'account'}. Verified via BBPS.`,
      });

      setTimeout(async () => {
        await onConfirmVerification(
          bill.id,
          'BBPS_VERIFIED',
          `${selectedApp} (BBPS Auto-Verified)`
        );
        onClose();
      }, 1200);
    }, 1500);
  };

  // 2. Manual Self-Report (with warning tag so family knows)
  const handleSelfReport = async () => {
    setIsVerifying(true);
    setTimeout(async () => {
      await onConfirmVerification(
        bill.id,
        'SELF_REPORTED',
        `${selectedApp} (Self-Reported)`
      );
      setIsVerifying(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 bg-stone-900/60 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4 animate-fade-in">
      <div className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 border border-stone-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-amber-100 text-amber-900 flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5 text-amber-800" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-stone-900 leading-tight">
                Check Payment Before Marking
              </h3>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Prevent missed bills and unexpected service cutoffs
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

        {/* Bill Summary Card */}
        <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200/80 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-stone-900">{bill.title}</div>
            <div className="text-[10px] text-stone-500 mt-0.5">
              {bill.consumerNumber || 'Consumer Account'} • Due: Tomorrow
            </div>
          </div>
          <div className="text-right">
            <div className="text-base font-black text-stone-900">
              ₹{bill.amount.toLocaleString('en-IN')}
            </div>
            <span className="text-[9px] font-bold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded-full">
              Pending Check
            </span>
          </div>
        </div>

        {/* Why this matters (Simple English Warning) */}
        <div className="p-3 rounded-2xl bg-amber-50/70 border border-amber-200/70 text-xs text-amber-950 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed text-amber-900">
            <strong>Why we check:</strong> If you mark this as paid without paying, other family members will think it is settled, and your electricity or WiFi could get disconnected.
          </p>
        </div>

        {/* Action 1: Which app did you use? */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-stone-800 block">
            Where did you pay this bill?
          </label>
          <div className="grid grid-cols-4 gap-2">
            {['PhonePe', 'Google Pay', 'Paytm', 'Bank NetBanking'].map(app => (
              <button
                key={app}
                type="button"
                onClick={() => setSelectedApp(app)}
                className={`py-2 px-1.5 rounded-xl text-[10px] font-bold border transition-all text-center ${
                  selectedApp === app
                    ? 'bg-emerald-800 text-white border-emerald-900 shadow-xs'
                    : 'bg-stone-50 text-stone-700 border-stone-200 hover:bg-stone-100'
                }`}
              >
                {app}
              </button>
            ))}
          </div>
        </div>

        {/* Verification Status Feedback */}
        {verificationResult.status === 'success' && (
          <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center gap-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span className="text-[11px] font-semibold">{verificationResult.message}</span>
          </div>
        )}

        {/* Main Action Buttons */}
        <div className="space-y-2 pt-1">
          {/* Recommended Option: Auto-Verify with Provider */}
          <button
            onClick={handleAutoVerifyWithBBPS}
            disabled={isVerifying}
            className="w-full py-3 px-4 rounded-2xl bg-emerald-800 hover:bg-emerald-900 text-white font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-all active:scale-98 disabled:opacity-50"
          >
            {isVerifying ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-300" />
                <span>Checking with {bill.title}...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-300" />
                <span>Verify with Biller (Auto-Check BBPS)</span>
              </>
            )}
          </button>

          {/* Self-Report with Notice */}
          <button
            onClick={handleSelfReport}
            disabled={isVerifying}
            className="w-full py-2.5 px-4 rounded-2xl bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>I Already Paid on {selectedApp} (Mark as Paid)</span>
          </button>

          {/* Cancel button */}
          <button
            onClick={onClose}
            disabled={isVerifying}
            className="w-full py-2 text-center text-xs font-semibold text-stone-400 hover:text-stone-700 transition-colors"
          >
            Cancel — I haven't paid yet
          </button>
        </div>
      </div>
    </div>
  );
}
