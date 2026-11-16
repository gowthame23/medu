"use client";

import React, { useState, useEffect } from "react";
import { X, Mail, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface VerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  userEmail: string;
  onVerified: () => void;
}

export default function VerificationModal({
  isOpen,
  onClose,
  userEmail,
  onVerified,
}: VerificationModalProps) {
  const [code, setCode] = useState("");
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
    setError(null);
    setSuccessMessage(null);
    onClose();
  };

  const handleSendCode = async () => {
    if (countdown > 0 || isSending) return;
    setIsSending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await api.verification.sendEmail();
      setCountdown(60);
      setSuccessMessage("Verification code dispatched to your email.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send code. Please try again.";
      setError(msg);
    } finally {
      setIsSending(false);
    }
  };

  const handleConfirmCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length !== 6 || isConfirming) return;
    setIsConfirming(true);
    setError(null);
    try {
      await api.verification.confirmEmail(code.trim());
      setSuccessMessage("Email successfully verified!");
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
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900">Verify Email</h2>
              <p className="text-xs text-stone-500 font-mono">{userEmail}</p>
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

        <form onSubmit={handleConfirmCode} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1.5">
              6-Digit Verification Code
            </label>
            <input
              type="text"
              data-testid="verification-code-input"
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
              onClick={handleSendCode}
              disabled={isSending || countdown > 0}
              className="text-emerald-800 hover:text-emerald-900 font-medium disabled:text-stone-400 transition"
            >
              {isSending ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending code...
                </span>
              ) : countdown > 0 ? (
                `Resend code in ${countdown}s`
              ) : (
                "Send Verification Code"
              )}
            </button>
          </div>

          <button
            type="submit"
            data-testid="confirm-verification-btn"
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
      </div>
    </div>
  );
}
