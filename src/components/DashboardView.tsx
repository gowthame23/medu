"use client";

import React, { useState } from "react";
import {
  Calendar,
  Plus,
  Clock,
  ShieldCheck,
  Zap,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";
import { BillRadarItem, DailyLog } from "@/lib/api";
import SafeVerifyPaymentModal from "@/components/SafeVerifyPaymentModal";

interface DashboardViewProps {
  currentMode: "individual" | "family";
  tomorrowRadars: BillRadarItem[];
  allRadars: BillRadarItem[];
  recentLogs: DailyLog[];
  onOpenCheckIn: () => void;
  onOpenAddRadar: () => void;
  onOpenUPIIntentModal: (bill: BillRadarItem) => void;
  onRefreshDashboard: () => void;
  familyId?: string;
}

export default function DashboardView({
  currentMode,
  tomorrowRadars,
  allRadars,
  recentLogs,
  onOpenCheckIn,
  onOpenAddRadar,
  onOpenUPIIntentModal,
  onRefreshDashboard,
  familyId,
}: DashboardViewProps) {
  const [activeRadarFilter, setActiveRadarFilter] = useState<"tomorrow" | "all">("tomorrow");
  const [verifyModalBill, setVerifyModalBill] = useState<BillRadarItem | null>(null);

  const displayedRadars = activeRadarFilter === "tomorrow" ? tomorrowRadars : allRadars;

  return (
    <div className="space-y-4 px-4 pt-2 pb-24 animate-fade-in">
      {/* 1. Daily Ritual Action Card */}
      <div className="p-4 rounded-3xl bg-gradient-to-br from-emerald-800 to-emerald-950 text-white shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">
              Nightly 30s Check-in
            </span>
            <h3 className="text-sm font-extrabold text-white">Daily Spending Awareness</h3>
          </div>
          <button
            onClick={onOpenCheckIn}
            className="px-3 py-1.5 bg-white text-emerald-950 hover:bg-emerald-50 text-xs font-bold rounded-xl transition shadow-xs active:scale-[0.98]"
          >
            Check In
          </button>
        </div>
        <p className="text-[11px] text-emerald-100/90 leading-relaxed">
          Log daily expenses without guilt or complex budget rules. Awareness removes financial anxiety.
        </p>
      </div>

      {/* 2. Tomorrow's Radar / Upcoming Bills */}
      <div className="p-4 rounded-3xl bg-white border border-stone-200/80 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
              {activeRadarFilter === "tomorrow" ? "Tomorrow's Radar" : "Upcoming Bills"}
            </h3>
            <span className="text-[10px] font-bold bg-stone-100 text-stone-600 px-2 py-0.5 rounded-full">
              {displayedRadars.length}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <div className="flex bg-stone-100 p-0.5 rounded-xl text-[10px] font-bold">
              <button
                onClick={() => setActiveRadarFilter("tomorrow")}
                className={`px-2 py-0.5 rounded-lg transition ${
                  activeRadarFilter === "tomorrow"
                    ? "bg-white text-stone-900 shadow-2xs"
                    : "text-stone-500 hover:text-stone-800"
                }`}
              >
                Tomorrow
              </button>
              <button
                onClick={() => setActiveRadarFilter("all")}
                className={`px-2 py-0.5 rounded-lg transition ${
                  activeRadarFilter === "all"
                    ? "bg-white text-stone-900 shadow-2xs"
                    : "text-stone-500 hover:text-stone-800"
                }`}
              >
                All
              </button>
            </div>
            <button
              onClick={onOpenAddRadar}
              className="p-1 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white transition"
              title="Add reminder"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {displayedRadars.length === 0 ? (
          <div className="py-8 text-center space-y-1.5">
            <ShieldCheck className="w-7 h-7 text-emerald-600 mx-auto" />
            <p className="text-xs font-bold text-stone-800">Clear Skies Tomorrow</p>
            <p className="text-[11px] text-stone-500">
              No bills due {activeRadarFilter === "tomorrow" ? "tomorrow" : "in the upcoming radar"}.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {displayedRadars.map((bill) => (
              <div
                key={bill.id}
                className="p-3.5 rounded-2xl bg-stone-50/80 border border-stone-200/70 hover:border-stone-300 transition space-y-2.5"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-stone-900">{bill.title}</span>
                      <span className="text-[9px] font-semibold bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded">
                        {bill.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-[10px] text-stone-500 font-mono">
                      <span>{bill.consumer_number_masked || "Direct Utility"}</span>
                      <span>•</span>
                      <span>Due: {bill.due_date}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-black text-stone-900 font-mono">
                      ₹{bill.amount}
                    </span>
                  </div>
                </div>

                {/* Status & Actions */}
                <div className="flex items-center justify-between pt-1 border-t border-stone-100">
                  <div className="flex items-center gap-1.5 text-[10px]">
                    {bill.bill_status === "PAID" ? (
                      <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Paid & Verified</span>
                      </span>
                    ) : bill.bill_status === "PAID_UNVERIFIED" ? (
                      <span className="flex items-center gap-1 text-amber-700 font-semibold" title="Self-reported payment waiting for biller reconciliation">
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>Self-Reported ({bill.paid_by_display_name || "Unverified"})</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-stone-500">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Unpaid</span>
                      </span>
                    )}
                  </div>

                  {!bill.is_paid && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onOpenUPIIntentModal(bill)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-800 hover:bg-emerald-900 text-white rounded-xl text-[11px] font-bold shadow-2xs transition"
                      >
                        <Zap className="w-3 h-3 fill-white" />
                        <span>Pay via UPI</span>
                      </button>

                      <button
                        onClick={() => setVerifyModalBill(bill)}
                        className="px-2.5 py-1.5 bg-stone-200/80 hover:bg-stone-300 text-stone-700 rounded-xl text-[11px] font-bold transition"
                      >
                        Mark Paid
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. Recent 7-Day Expense Logs */}
      <div className="p-4 rounded-3xl bg-white border border-stone-200/80 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
            Recent Check-Ins
          </h3>
          <Calendar className="w-4 h-4 text-stone-400" />
        </div>

        {recentLogs.length === 0 ? (
          <p className="text-xs text-stone-500 text-center py-4">
            No check-in entries yet. Tap &apos;Check In&apos; above to record today&apos;s spending.
          </p>
        ) : (
          <div className="space-y-2">
            {recentLogs.map((log) => (
              <div
                key={log.id}
                className="p-3 rounded-2xl bg-stone-50 border border-stone-100 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-bold text-stone-800">{log.log_date}</div>
                  <div className="text-[10px] text-stone-500 mt-0.5">
                    {log.entries.length} categor{log.entries.length === 1 ? "y" : "ies"} logged
                    {log.notes ? ` • "${log.notes}"` : ""}
                  </div>
                </div>
                <div className="font-mono font-black text-stone-900">
                  ₹{log.total_spent}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Safe Verify Payment Modal for Self-Reported Payments */}
      <SafeVerifyPaymentModal
        isOpen={Boolean(verifyModalBill)}
        onClose={() => setVerifyModalBill(null)}
        bill={verifyModalBill}
        currentMode={currentMode}
        familyId={familyId}
        onSuccess={onRefreshDashboard}
      />
    </div>
  );
}
