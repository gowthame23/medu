"use client";

import React, { useState, useEffect } from "react";
import { X, Phone, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface PhoneVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPhone?: string | null;
  onVerified: () => void;
}

export default function PhoneVerificationModal({
  isOpen,
  onClose,
  currentPhone,
  onVerified,
}: PhoneVerificationModalProps) {
  const [phone, setPhone] = useState(currentPhone || "");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [isSending, setIsSending] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [countdown]);

  if (!isOpen) return null;

  const handleClose = () => {
    setCode("");
    setStep("phone");
    setError(null);
    setSuccessMessage(null);
    onClose();
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() || isSending) return;
    setIsSending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await api.verification.sendPhone(phone.trim());
      setStep("code");
      setCountdown(60);
      setSuccessMessage("Verification code dispatched via SMS.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid phone number or dispatch failed.";
      setError(msg);
    } finally {
      setIsSending(false);
    }
  };

  const handleConfirmOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length !== 6 || isConfirming) return;
    setIsConfirming(true);
    setError(null);
    try {
      await api.verification.confirmPhone(code.trim());
      setSuccessMessage("Phone number verified successfully!");
      setTimeout(() => {
        onVerified();
        onClose();
      }, 800);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid or expired verification code.";
      setError(msg);
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl w-full max-w-md p-6 shadow-2xl border border-stone-100 flex flex-col gap-5">
        <div className="flex items-center justify-between pb-3 border-b border-stone-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-800">
              <Phone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900">Verify Phone Number</h2>
              <p className="text-xs text-stone-500">Standard E.164 phone verification</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-full hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 text-red-700 text-xs rounded-xl flex items-center gap-2 border border-red-100">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3 bg-emerald-50 text-emerald-800 text-xs rounded-xl flex items-center gap-2 border border-emerald-100">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {step === "phone" ? (
          <form onSubmit={handleSendOtp} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1.5">
                Phone Number (E.164 or 10-digit)
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full text-base font-mono py-3 px-4 rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-emerald-700/20 focus:border-emerald-700"
              />
              <p className="text-[11px] text-stone-400 mt-1">
                Bare 10-digit Indian numbers will automatically receive the +91 prefix.
              </p>
            </div>

            <button
              type="submit"
              disabled={!phone.trim() || isSending}
              className="w-full py-3 px-4 rounded-xl bg-emerald-800 hover:bg-emerald-900 text-white font-medium text-sm flex items-center justify-center gap-2 disabled:bg-stone-200 disabled:text-stone-400 transition shadow-sm"
            >
              {isSending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Sending OTP...</span>
                </>
              ) : (
                <span>Send Verification Code</span>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirmOtp} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1.5">
                6-Digit SMS Code sent to {phone}
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="123456"
                maxLength={6}
                className="w-full text-center text-2xl tracking-[0.3em] font-mono font-bold py-3 px-4 rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-emerald-700/20 focus:border-emerald-700"
              />
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <button
                type="button"
                onClick={() => setStep("phone")}
                className="text-stone-500 hover:text-stone-700 transition"
              >
                Change number
              </button>
              <button
                type="button"
                onClick={handleSendOtp}
                disabled={isSending || countdown > 0}
                className="text-emerald-800 hover:text-emerald-900 font-medium disabled:text-stone-400 transition"
              >
                {countdown > 0 ? `Resend in ${countdown}s` : "Resend SMS"}
              </button>
            </div>

            <button
              type="submit"
              disabled={code.length !== 6 || isConfirming}
              className="w-full py-3 px-4 rounded-xl bg-emerald-800 hover:bg-emerald-900 text-white font-medium text-sm flex items-center justify-center gap-2 disabled:bg-stone-200 disabled:text-stone-400 transition shadow-sm"
            >
              {isConfirming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying...</span>
                </>
              ) : (
                <span>Confirm & Verify</span>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
