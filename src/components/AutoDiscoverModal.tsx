'use client';

import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Phone,
  Mail,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  Building,
  Zap,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import confetti from 'canvas-confetti';

interface AutoDiscoverModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AutoDiscoverModal({ isOpen, onClose, onSuccess }: AutoDiscoverModalProps) {
  const [step, setStep] = useState<'input' | 'otp' | 'scanning' | 'results'>('input');
  const [phone, setPhone] = useState('98450 12345');
  const [email, setEmail] = useState('gowtham@gmail.com');
  const [otp, setOtp] = useState('4921');
  const [discoveredData, setDiscoveredData] = useState<any>(null);
  const [isImporting, setIsImporting] = useState(false);

  if (!isOpen) return null;

  const handleSendOtp = (e: React.FormEvent) => {
    e.preventDefault();
    setStep('otp');
  };

  const handleVerifyOtp = async () => {
    setStep('scanning');

    try {
      const res = await fetch('/api/auto-discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, email }),
      });

      if (res.ok) {
        const data = await res.json();
        // Give 1.5 seconds for the scanning animation
        setTimeout(() => {
          setDiscoveredData(data);
          setStep('results');
        }, 1500);
      }
    } catch (err) {
      console.error('Discovery error:', err);
      setStep('input');
    }
  };

  const handleImportAll = () => {
    setIsImporting(true);
    confetti({
      particleCount: 65,
      spread: 70,
      origin: { y: 0.7 },
      colors: ['#059669', '#10b981', '#f59e0b', '#3b82f6'],
    });

    setTimeout(() => {
      onSuccess();
      onClose();
      setIsImporting(false);
      setStep('input');
    }, 1200);
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
                <Sparkles className="w-4 h-4 text-emerald-700" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-stone-900 leading-none">
                  Auto-Discover Household
                </h3>
                <span className="text-[10px] text-stone-500">
                  RBI Account Aggregator &amp; BBPS Powered
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

        {/* STEP 1: PHONE & EMAIL INPUT */}
        {step === 'input' && (
          <form onSubmit={handleSendOtp} className="space-y-4 pt-1">
            <div className="p-3.5 bg-emerald-50/70 rounded-2xl border border-emerald-100 text-xs text-emerald-950 flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Enter your mobile number &amp; email. The system automatically connects with **RBI Account Aggregator** and **BBPS** to discover all your active autopays, loans, and bills in one place.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1">
                Mobile Number (Linked to Bank / Aadhaar)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-xs text-stone-500 font-bold">+91</span>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  className="w-full pl-12 pr-3 py-2 text-xs font-bold rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-stone-200 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              />
            </div>

            <button
              type="submit"
              className="w-full py-3.5 rounded-2xl text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-1.5 shadow-md"
            >
              <span>Send Secure Verification OTP</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>
        )}

        {/* STEP 2: OTP VERIFICATION */}
        {step === 'otp' && (
          <div className="space-y-4 pt-2 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-emerald-100 flex items-center justify-center text-emerald-800 font-bold">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-stone-900">Enter Verification Code</h4>
              <p className="text-[11px] text-stone-500 mt-0.5">
                Sent to +91 {phone} for RBI Account Aggregator consent
              </p>
            </div>

            <input
              type="text"
              maxLength={4}
              value={otp}
              onChange={e => setOtp(e.target.value)}
              className="w-36 mx-auto text-center tracking-[10px] text-2xl font-black py-2 rounded-xl border-2 border-emerald-600 bg-stone-50 focus:outline-none"
            />

            <button
              onClick={handleVerifyOtp}
              className="w-full py-3.5 rounded-2xl text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-1.5 shadow-md"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Verify &amp; Discover All Bills</span>
            </button>
          </div>
        )}

        {/* STEP 3: SCANNING ANIMATION */}
        {step === 'scanning' && (
          <div className="py-8 text-center space-y-3">
            <Loader2 className="w-10 h-10 text-emerald-700 animate-spin mx-auto" />
            <h4 className="text-sm font-bold text-stone-900">Scanning Your Household Financials...</h4>
            <div className="space-y-1.5 text-[11px] text-stone-500 max-w-xs mx-auto">
              <div className="flex items-center justify-between text-emerald-800 font-medium">
                <span>✓ Connecting RBI Account Aggregator</span>
                <span>Active</span>
              </div>
              <div className="flex items-center justify-between text-emerald-800 font-medium">
                <span>✓ NPCI BBPS Biller Registry</span>
                <span>Found 2</span>
              </div>
              <div className="flex items-center justify-between text-emerald-800 font-medium">
                <span>✓ UPI AutoPay Mandate Directory</span>
                <span>Found 2</span>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: RESULTS REVIEW */}
        {step === 'results' && discoveredData && (
          <div className="space-y-4 pt-1">
            <div className="p-3 bg-emerald-50 rounded-2xl border border-emerald-200 text-center">
              <span className="text-[10px] text-emerald-800 uppercase font-extrabold tracking-wider">
                Discovery Complete
              </span>
              <div className="text-sm font-black text-emerald-950 mt-0.5">
                Found {discoveredData.discoveredBills.length} Active Bills &amp; {discoveredData.discoveredLiabilities.length} Loans
              </div>
              <p className="text-[10px] text-emerald-700 mt-0.5">
                Automatically matched to +91 {phone}
              </p>
            </div>

            {/* Discovered Items List */}
            <div className="space-y-2 max-h-56 overflow-y-auto">
              <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider px-1">
                Discovered Upcoming Bills &amp; Autopays:
              </div>
              {discoveredData.discoveredBills.map((b: any, idx: number) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl border border-stone-200 bg-stone-50/70 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-stone-900">{b.title}</div>
                    <div className="text-[10px] text-stone-500 font-mono">{b.source}</div>
                  </div>
                  <div className="font-bold text-stone-900">₹{b.amount.toLocaleString('en-IN')}</div>
                </div>
              ))}

              <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider px-1 pt-1">
                Discovered Loans &amp; Liabilities:
              </div>
              {discoveredData.discoveredLiabilities.map((l: any, idx: number) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl border border-stone-200 bg-stone-50/70 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-stone-900">{l.loanName}</div>
                    <div className="text-[10px] text-stone-500">Rate: {l.interestRate}%</div>
                  </div>
                  <div className="font-bold text-stone-900">
                    ₹{(l.principalAmount / 100000).toFixed(0)} Lakhs
                  </div>
                </div>
              ))}
            </div>

            {/* 1-Tap Import CTA */}
            <button
              onClick={handleImportAll}
              disabled={isImporting}
              className="w-full py-3.5 rounded-2xl text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white transition-all active:scale-98 flex items-center justify-center gap-1.5 shadow-md disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-emerald-200" />
              <span>{isImporting ? 'Syncing into Vault...' : 'Sync All into My Radar & Vault (1-Tap)'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
