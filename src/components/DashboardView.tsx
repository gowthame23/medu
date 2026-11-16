'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Flame,
  CheckCircle2,
  Calendar,
  AlertCircle,
  Plus,
  ArrowRight,
  TrendingUp,
  Clock,
  Check,
  ShieldCheck,
  ExternalLink,
  ChevronRight,
  Lock,
  RefreshCw,
  Zap,
  Users,
  Shield,
  Smartphone,
} from 'lucide-react';
import { UpcomingRadarRecord, DailyLogRecord, CURRENT_USER, PARTNER_USER, DEFAULT_FAMILY_GROUP } from '@/lib/dataStore';
import SafeVerifyPaymentModal from '@/components/SafeVerifyPaymentModal';

interface DashboardViewProps {
  currentMode: 'individual' | 'family';
  streak: number;
  isTodayLogged: boolean;
  todayCheckIn: DailyLogRecord | null;
  tomorrowRadars: UpcomingRadarRecord[];
  allRadars: UpcomingRadarRecord[];
  recentLogs: DailyLogRecord[];
  onOpenCheckIn: () => void;
  onOpenAddRadar: () => void;
  onOpenUPIIntentModal: (bill: UpcomingRadarRecord) => void;
  onToggleRadarPaid: (id: string) => void;
  onAutoSyncBills: () => void;
  onOpenAutoDiscover?: () => void;
  isAutoSyncing?: boolean;
  syncMessage?: string | null;
  onNavigateToVault: () => void;
  activeUserName?: string;
  vaultSummary?: {
    activeLoansCount: number;
    totalDailyDebtCost: number;
  };
}

export default function DashboardView({
  currentMode,
  streak,
  isTodayLogged,
  todayCheckIn,
  tomorrowRadars,
  allRadars,
  recentLogs,
  onOpenCheckIn,
  onOpenAddRadar,
  onOpenUPIIntentModal,
  onToggleRadarPaid,
  onAutoSyncBills,
  onOpenAutoDiscover,
  isAutoSyncing = false,
  syncMessage = null,
  onNavigateToVault,
  activeUserName = 'Gowtham',
  vaultSummary,
}: DashboardViewProps) {
  const [activeRadarFilter, setActiveRadarFilter] = useState<'tomorrow' | 'all'>('tomorrow');
  const [greeting, setGreeting] = useState<string>('Welcome');
  const [verifyModalBill, setVerifyModalBill] = useState<UpcomingRadarRecord | null>(null);

  const handleConfirmVerification = async (
    billId: string,
    verificationType: 'BBPS_VERIFIED' | 'SELF_REPORTED',
    paymentMethod: string
  ) => {
    try {
      await fetch(`/api/radar/${billId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paidBy: activeUserName,
          paymentMethod,
          syncSource: verificationType === 'BBPS_VERIFIED' ? 'BBPS Auto-Verified' : 'Self-Reported',
          paymentRef: verificationType === 'BBPS_VERIFIED'
            ? `BBPS-${Math.floor(100000 + Math.random() * 900000)}`
            : `UNCONFIRMED`,
        }),
      });
      onToggleRadarPaid(billId);
    } catch (err) {
      console.error('Failed to verify bill payment:', err);
    }
  };

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good morning');
    else if (hour < 17) setGreeting('Good afternoon');
    else setGreeting('Good evening');
  }, []);

  const displayedRadars = activeRadarFilter === 'tomorrow' ? tomorrowRadars : allRadars;
  const unpaidTomorrow = tomorrowRadars.filter(r => !r.isPaid);
  const tomorrowTotal = unpaidTomorrow.reduce((sum, r) => sum + r.amount, 0);

  return (
    <div className="space-y-4 px-4 pt-3 pb-24 animate-fade-in">
      {/* ============================================================== */}
      {/* 1. HERO ZONE (MODE-AWARE: INDIVIDUAL vs FAMILY HUB) */}
      {/* ============================================================== */}
      {currentMode === 'individual' ? (
        <div className="bg-white rounded-3xl p-5 border border-stone-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-100/70 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-700" />
                <span>My Private Space</span>
              </span>
              <h1 className="text-xl font-extrabold text-stone-900 mt-1.5 tracking-tight">
                {greeting}, {activeUserName}
              </h1>
            </div>

            <div className="text-right">
              <span className="text-[10px] text-stone-400 font-medium block">Today</span>
              <span className="text-xs font-bold text-stone-600">
                {new Date().toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
              </span>
            </div>
          </div>

          {/* Daily Win Action Tile */}
          <div
            onClick={onOpenCheckIn}
            className={`mt-3.5 p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between active:scale-98 ${
              isTodayLogged
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                : 'bg-stone-50 border-stone-200 hover:border-emerald-700/40'
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                  isTodayLogged
                    ? 'bg-emerald-600 text-white'
                    : 'bg-emerald-100/80 text-emerald-800'
                }`}
              >
                {isTodayLogged ? (
                  <CheckCircle2 className="w-5 h-5 text-white" />
                ) : (
                  <Clock className="w-5 h-5 text-emerald-800" />
                )}
              </div>
              <div>
                <div className="text-xs font-bold text-stone-900">
                  {isTodayLogged ? "Today's Check-in Done ✨" : '30-Second Evening Check-in'}
                </div>
                <div className="text-[11px] text-stone-500 mt-0.5">
                  {isTodayLogged && todayCheckIn
                    ? `₹${todayCheckIn.totalSpent.toLocaleString('en-IN')} logged • Tap to change`
                    : "Log today's spending in 30 seconds. No receipts needed."}
                </div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-stone-400 shrink-0" />
          </div>

          {/* Auto-Discover Prompt */}
          {onOpenAutoDiscover && (
            <div
              onClick={onOpenAutoDiscover}
              className="mt-2.5 p-2.5 rounded-2xl bg-gradient-to-r from-emerald-50/80 via-white to-amber-50/40 border border-emerald-200/80 cursor-pointer flex items-center justify-between active:scale-98 transition-transform"
            >
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-emerald-800 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
                  ✨
                </div>
                <div>
                  <div className="text-[11px] font-bold text-stone-900 leading-none">
                    Find Bills &amp; Loans Automatically
                  </div>
                  <div className="text-[9px] text-stone-500 mt-0.5">
                    Connect with your phone &amp; email to import your bills
                  </div>
                </div>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-stone-400 shrink-0" />
            </div>
          )}
        </div>
      ) : (
        /* FAMILY SHARED HUB HEADER (STRICTLY SANDBOXED: ZERO PERSONAL DEBT) */
        <div className="bg-white rounded-3xl p-5 border border-stone-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
                <Users className="w-3 h-3 text-emerald-700" />
                <span>Family Shared Hub</span>
              </span>
              <h1 className="text-xl font-extrabold text-stone-900 mt-1 tracking-tight">
                {DEFAULT_FAMILY_GROUP.groupName}
              </h1>
            </div>

            <div className="text-right">
              <span className="text-[10px] text-stone-400 font-medium block">Active Members</span>
              <div className="flex items-center gap-1 justify-end mt-0.5">
                <span className="w-5 h-5 rounded-full bg-emerald-800 text-white text-[9px] font-bold flex items-center justify-center">
                  G
                </span>
                <span className="w-5 h-5 rounded-full bg-purple-700 text-white text-[9px] font-bold flex items-center justify-center">
                  P
                </span>
                <span className="text-[10px] text-stone-600 font-semibold ml-0.5">2 Members</span>
              </div>
            </div>
          </div>

          {/* Strict Privacy Shield Banner */}
          <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200 text-xs text-stone-600 flex items-start gap-2">
            <Shield className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
            <p className="text-[10px] leading-relaxed text-stone-600">
              <strong className="text-stone-900 font-bold">Family Privacy Shield:</strong> Your personal loans and debts are 100% private. Only shared home bills (like power, WiFi, and gas) are shown here.
            </p>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* 2. TOMORROW’S RADAR (PROACTIVE & AUTOMATED UPI INTENT) */}
      {/* ============================================================== */}
      <div className="bg-white rounded-3xl p-5 border border-stone-200/80 shadow-xs space-y-4">
        {/* Radar Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-stone-900 tracking-tight">
                {currentMode === 'family' ? "Family Tomorrow's Radar" : "Tomorrow's Radar"}
              </h2>
              <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.2 rounded-full">
                1-Tap UPI Intent
              </span>
            </div>
            <p className="text-[11px] text-stone-500 mt-0.5">
              {currentMode === 'family'
                ? 'Shared home bills due tomorrow'
                : 'Bills due tomorrow • Automatically marks as paid when you pay'}
            </p>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Auto-Sync BBPS & Bank Button */}
            <button
              onClick={onAutoSyncBills}
              disabled={isAutoSyncing}
              className="px-2.5 py-1 text-[11px] font-bold rounded-xl border border-stone-200 bg-stone-50 text-stone-700 hover:bg-stone-100 flex items-center gap-1 transition-colors active:scale-95 disabled:opacity-50"
              title="Automatically scan BBPS and bank SMS for settled bills"
            >
              <RefreshCw className={`w-3 h-3 ${isAutoSyncing ? 'animate-spin text-emerald-700' : 'text-stone-500'}`} />
              <span className="text-[10px] font-bold">{isAutoSyncing ? 'Syncing...' : 'Sync'}</span>
            </button>

            <button
              onClick={onOpenAddRadar}
              className="w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-700 flex items-center justify-center transition-colors"
              title="Add reminder"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Sync Feedback Message */}
        {syncMessage && (
          <div className="p-2.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center gap-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="text-[11px] font-medium leading-tight">{syncMessage}</span>
          </div>
        )}

        {/* Time Filter Pills */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveRadarFilter('tomorrow')}
            className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
              activeRadarFilter === 'tomorrow'
                ? 'bg-stone-900 text-white'
                : 'bg-stone-100 text-stone-600'
            }`}
          >
            Tomorrow ({tomorrowRadars.length})
          </button>
          <button
            onClick={() => setActiveRadarFilter('all')}
            className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
              activeRadarFilter === 'all'
                ? 'bg-stone-900 text-white'
                : 'bg-stone-100 text-stone-600'
            }`}
          >
            All Bills ({allRadars.length})
          </button>
        </div>

        {/* Radar Bills Cards */}
        {displayedRadars.length === 0 ? (
          <div className="text-center py-8 px-4 rounded-2xl bg-emerald-50/50 border border-emerald-100">
            <CheckCircle2 className="w-7 h-7 text-emerald-600 mx-auto mb-1.5" />
            <div className="text-xs font-bold text-stone-900">Clear Horizon</div>
            <p className="text-[11px] text-stone-500 mt-0.5">
              No bills scheduled. You are completely ahead!
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {displayedRadars.map(item => {
              const isTomorrow = tomorrowRadars.some(t => t.id === item.id);

              return (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-2xl border transition-all flex flex-col gap-2.5 ${
                    item.isPaid
                      ? 'bg-emerald-50/40 border-emerald-200/80 shadow-2xs'
                      : isTomorrow
                      ? 'bg-white border-amber-300/80 shadow-2xs'
                      : 'bg-white border-stone-200'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`text-xs font-bold truncate ${
                            item.isPaid ? 'text-emerald-950 font-extrabold' : 'text-stone-900'
                          }`}
                        >
                          {item.title}
                        </span>

                        {/* Family Shared Badge vs Individual */}
                        {item.familyGroupId ? (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800">
                            Shared Utility
                          </span>
                        ) : (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-stone-100 text-stone-700">
                            Personal Bill
                          </span>
                        )}

                        {item.isPaid && (
                          <span className="text-[9px] font-bold text-emerald-800 bg-emerald-100/90 px-2 py-0.2 rounded-full inline-flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" /> Paid &amp; Settled
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-2 text-[10px] text-stone-500 mt-1">
                        {item.consumerNumber && (
                          <span className="font-mono text-stone-600 bg-stone-100 px-1 py-0.2 rounded">
                            {item.consumerNumber}
                          </span>
                        )}
                        <span>Due: Tomorrow</span>
                      </div>
                    </div>

                    {/* Price Tag */}
                    <div className="text-right shrink-0">
                      <div
                        className={`text-sm font-extrabold ${
                          item.isPaid ? 'text-stone-400 line-through' : 'text-stone-900'
                        }`}
                      >
                        ₹{item.amount.toLocaleString('en-IN')}
                      </div>
                      {item.isPaid && (
                        <div className="text-[10px] text-emerald-700 font-bold">₹0 Due</div>
                      )}
                    </div>
                  </div>

                  {/* Payment Proof / 1-Tap UPI Intent Action Row */}
                  <div className="pt-2 border-t border-stone-100 flex items-center justify-between gap-2">
                    {item.isPaid ? (
                      item.syncSource === 'Self-Reported' ? (
                        <div className="text-[10px] text-amber-900 bg-amber-50/90 px-2 py-0.5 rounded-lg border border-amber-200/90 flex items-center gap-1.5 flex-wrap">
                          <span className="font-bold">⚠️ Self-Reported:</span>
                          <span>Paid by {item.paidByName} ({item.paymentMethod})</span>
                          <span className="text-[9px] text-amber-700 bg-amber-100 px-1 py-0.2 rounded font-semibold">
                            Checking with biller...
                          </span>
                        </div>
                      ) : (
                        <div className="text-[10px] text-stone-600 flex items-center gap-1.5 flex-wrap">
                          <span className="font-bold text-emerald-900">
                            ✓ Paid by {item.paidByName || 'Gowtham'}
                          </span>
                          <span>•</span>
                          <span className="text-stone-500">{item.paymentMethod || 'UPI'}</span>
                          <span>•</span>
                          <span className="font-mono text-stone-400">
                            {item.paymentRef || 'Ref: UPI-984210'}
                          </span>
                        </div>
                      )
                    ) : (
                      <div className="text-[10px] text-stone-500 flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                        <span>BBPS Verified Biller</span>
                      </div>
                    )}

                    <div className="flex items-center gap-1.5 shrink-0">
                      {item.isPaid ? (
                        <button
                          onClick={() => onToggleRadarPaid(item.id)}
                          className="px-2.5 py-1 rounded-xl text-[10px] font-bold bg-stone-100 text-stone-500 hover:bg-stone-200 transition-colors"
                          title="Undo payment if needed"
                        >
                          Undo
                        </button>
                      ) : (
                        <>
                          {/* 1-Tap UPI Intent Button */}
                          <button
                            onClick={() => onOpenUPIIntentModal(item)}
                            className="px-3 py-1.5 rounded-xl text-[11px] font-bold bg-emerald-800 text-white hover:bg-emerald-900 shadow-2xs flex items-center gap-1 transition-all active:scale-95"
                          >
                            <Zap className="w-3 h-3 text-emerald-300" />
                            <span>Pay via UPI</span>
                          </button>

                          {/* Safe Verify & Mark Button */}
                          <button
                            onClick={() => setVerifyModalBill(item)}
                            className="px-2 py-1.5 rounded-xl text-[10px] font-bold bg-stone-100 text-stone-700 hover:bg-stone-200 transition-colors"
                            title="Check payment proof before marking"
                          >
                            Mark Paid
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Tomorrow Total Due Summary */}
            {activeRadarFilter === 'tomorrow' && (
              <div className="pt-2 flex items-center justify-between text-xs text-stone-600 px-1 border-t border-stone-100">
                <span className="text-[11px]">
                  {unpaidTomorrow.length > 0
                    ? `Due tomorrow (${unpaidTomorrow.length} pending):`
                    : 'Tomorrow status:'}
                </span>
                <span className="font-extrabold text-stone-900 text-sm">
                  {unpaidTomorrow.length > 0 ? `₹${tomorrowTotal.toLocaleString('en-IN')}` : 'All Clear ✨ (₹0)'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ============================================================== */}
      {/* 3. INDIVIDUAL-ONLY SECTION: 7-DAY CONSISTENCY & LIABILITIES VAULT */}
      {/* ============================================================== */}
      {currentMode === 'individual' && (
        <>
          {/* 7-DAY CONSISTENCY BAR CHART */}
          <div className="bg-white rounded-3xl p-4 border border-stone-200/80 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-stone-900">Past 7 Days Spending</span>
                <span className="text-[10px] text-stone-400 block mt-0.5">Daily expense view</span>
              </div>
            </div>

            {/* Vertical Bar Chart */}
            <div className="pt-2 pb-1">
              {(() => {
                const logs7 = [...recentLogs.slice(0, 7)].reverse();
                const maxAmount = Math.max(...logs7.map(l => l.totalSpent), 100);

                return (
                  <div className="grid grid-cols-7 gap-1.5 items-end h-28 px-0.5">
                    {logs7.map((log, idx) => {
                      const dateObj = new Date(log.logDate);
                      const isToday = idx === logs7.length - 1;
                      const heightPercent = Math.max(14, Math.min(100, Math.round((log.totalSpent / maxAmount) * 100)));
                      const amountFormatted = log.totalSpent >= 1000
                        ? `₹${(log.totalSpent / 1000).toFixed(1)}k`
                        : `₹${log.totalSpent}`;

                      return (
                        <div
                          key={log.id || idx}
                          className="flex flex-col items-center h-full justify-end group transition-transform active:scale-95"
                        >
                          {/* Top Amount Badge */}
                          <span className={`text-[9px] font-bold mb-1.5 whitespace-nowrap transition-colors ${
                            isToday ? 'text-emerald-800 font-extrabold' : 'text-stone-700'
                          }`}>
                            {amountFormatted}
                          </span>

                          {/* Vertical Bar with Track */}
                          <div className={`w-full max-w-[26px] h-20 rounded-2xl p-1 flex flex-col justify-end transition-colors ${
                            isToday ? 'bg-emerald-50 border border-emerald-200' : 'bg-stone-100/90'
                          }`}>
                            <div
                              style={{ height: `${heightPercent}%` }}
                              className={`w-full rounded-xl transition-all duration-500 ${
                                isToday
                                  ? 'bg-emerald-600 shadow-2xs'
                                  : 'bg-emerald-800/80 group-hover:bg-emerald-700'
                              }`}
                            />
                          </div>

                          {/* Day Label */}
                          <span className={`text-[10px] uppercase mt-2 font-bold ${
                            isToday ? 'text-emerald-900 font-black' : 'text-stone-400'
                          }`}>
                            {dateObj.toLocaleDateString('en-IN', { weekday: 'short' })}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </div>

          {/* PRIVATE LIABILITIES VAULT INTENTIONAL TILE */}
          <div
            onClick={onNavigateToVault}
            className="p-4 rounded-3xl bg-stone-900 text-white cursor-pointer shadow-sm active:scale-98 transition-transform flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-2xl bg-stone-800 flex items-center justify-center text-emerald-400">
                <Lock className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-bold">Private Liabilities Vault (Sandboxed)</div>
                <div className="text-[10px] text-stone-400">
                  Daily debt cost &amp; prepayment savings • 100% hidden from family
                </div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-stone-400" />
          </div>
        </>
      )}

      {/* ============================================================== */}
      {/* 4. FAMILY-ONLY EXPLANATORY FOOTER (STRICT PRIVACY REASSURANCE) */}
      {/* ============================================================== */}
      {currentMode === 'family' && (
        <div className="p-4 rounded-3xl bg-emerald-50/60 border border-emerald-100 text-center space-y-1">
          <ShieldCheck className="w-6 h-6 text-emerald-700 mx-auto mb-1" />
          <h4 className="text-xs font-bold text-stone-900">Family Privacy Guarantee</h4>
          <p className="text-[11px] text-stone-600 max-w-xs mx-auto">
            Personal credit cards, loans, mortgages, and individual bank balances are permanently locked away in your private individual spaces.
          </p>
        </div>
      )}

      {/* Safe Payment Verification Modal */}
      <SafeVerifyPaymentModal
        isOpen={!!verifyModalBill}
        onClose={() => setVerifyModalBill(null)}
        bill={verifyModalBill}
        activeUserName={activeUserName}
        onConfirmVerification={handleConfirmVerification}
      />
    </div>
  );
}
