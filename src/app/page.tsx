"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import MobileHeader from "@/components/MobileHeader";
import MobileNavBar from "@/components/MobileNavBar";
import DashboardView from "@/components/DashboardView";
import LiabilitiesVaultView from "@/components/LiabilitiesVaultView";
import NightlyCheckInModal from "@/components/NightlyCheckInModal";
import AddRadarModal from "@/components/AddRadarModal";
import AddLoanModal from "@/components/AddLoanModal";
import UPIIntentModal from "@/components/UPIIntentModal";
import {
  api,
  BillRadarItem,
  DailyLog,
  LoanItem,
  FamilyGroup,
} from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  // Dual-Account Mode: 'individual' (Private Space) vs 'family' (Household Hub)
  const [currentMode, setCurrentMode] = useState<"individual" | "family">("individual");
  const [activeTab, setActiveTab] = useState<"dashboard" | "vault">("dashboard");

  // Household Family group state
  const [familyGroups, setFamilyGroups] = useState<FamilyGroup[]>([]);
  const activeFamily = familyGroups[0] || null;

  // Radar bills & logs
  const [tomorrowRadars, setTomorrowRadars] = useState<BillRadarItem[]>([]);
  const [allRadars, setAllRadars] = useState<BillRadarItem[]>([]);
  const [recentLogs, setRecentLogs] = useState<DailyLog[]>([]);
  const [loans, setLoans] = useState<LoanItem[]>([]);

  // Modals
  const [isCheckInOpen, setIsCheckInOpen] = useState<boolean>(false);
  const [isAddRadarOpen, setIsAddRadarOpen] = useState<boolean>(false);
  const [isAddLoanOpen, setIsAddLoanOpen] = useState<boolean>(false);
  const [selectedUPIBill, setSelectedUPIBill] = useState<BillRadarItem | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const refreshDashboard = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  // Redirect to login if unauthenticated once loading completes
  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  // Load family groups for household mode
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    async function loadFamilies() {
      try {
        const groups = await api.families.list();
        if (groups.length === 0) {
          const newGroup = await api.families.create(`${user?.display_name || "My"}'s Household`);
          if (isMounted) setFamilyGroups([newGroup]);
        } else {
          if (isMounted) setFamilyGroups(groups);
        }
      } catch {
        if (isMounted) setFamilyGroups([]);
      }
    }

    loadFamilies();

    return () => {
      isMounted = false;
    };
  }, [user]);

  // Load dashboard data respecting strict privacy partition
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    async function loadData() {
      try {
        if (currentMode === "individual") {
          const [radarData, allBills, rangeLogs, loanData] = await Promise.all([
            api.bills.getRadar(7),
            api.bills.listPersonal(),
            api.dailyLogs.getRange(
              new Date(Date.now() - 6 * 86400000).toISOString().split("T")[0],
              new Date().toISOString().split("T")[0]
            ),
            api.loans.list(),
          ]);
          if (isMounted) {
            setTomorrowRadars(radarData);
            setAllRadars(allBills);
            setRecentLogs(rangeLogs.logs || []);
            setLoans(loanData);
          }
        } else {
          if (isMounted) setLoans([]);
          if (activeFamily) {
            const [famRadar, famBills] = await Promise.all([
              api.families.getRadar(activeFamily.id, 7),
              api.families.listBills(activeFamily.id),
            ]);
            if (isMounted) {
              setTomorrowRadars(famRadar);
              setAllRadars(famBills);
            }
          } else {
            if (isMounted) {
              setTomorrowRadars([]);
              setAllRadars([]);
            }
          }
        }
      } catch (err) {
        console.error("Dashboard refresh error:", err);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [user, currentMode, activeFamily, refreshTrigger]);

  if (loading || !user) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-700 mb-2" />
        <p className="text-xs text-stone-500 font-medium">Securing session...</p>
      </div>
    );
  }

  const unpaidTomorrowCount = tomorrowRadars.filter((b) => !b.is_paid).length;
  const isTodayLogged = recentLogs.some(
    (l) => l.log_date === new Date().toISOString().split("T")[0] && l.entries.length > 0
  );

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#fafaf7] relative pb-20">
      <MobileHeader
        currentMode={currentMode}
        onSwitchMode={(mode) => {
          setCurrentMode(mode);
          if (mode === "family") setActiveTab("dashboard");
        }}
        user={user}
        familyGroupName={activeFamily ? activeFamily.group_name : "Household Hub"}
        onLogout={logout}
      />

      <main className="flex-1">
        {activeTab === "dashboard" ? (
          <DashboardView
            currentMode={currentMode}
            tomorrowRadars={tomorrowRadars}
            allRadars={allRadars}
            recentLogs={recentLogs}
            onOpenCheckIn={() => setIsCheckInOpen(true)}
            onOpenAddRadar={() => setIsAddRadarOpen(true)}
            onOpenUPIIntentModal={(bill) => setSelectedUPIBill(bill)}
            onRefreshDashboard={refreshDashboard}
            familyId={activeFamily?.id}
          />
        ) : (
          <LiabilitiesVaultView
            loans={loans}
            onOpenAddLoan={() => setIsAddLoanOpen(true)}
            onRefreshLoans={refreshDashboard}
            userName={user.display_name}
          />
        )}
      </main>

      {/* Persistent Bottom Navigation */}
      <MobileNavBar
        currentMode={currentMode}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenCheckIn={() => setIsCheckInOpen(true)}
        unpaidTomorrowCount={unpaidTomorrowCount}
        isTodayLogged={isTodayLogged}
        onAttemptVaultInFamilyMode={() => {
          alert("Liabilities Vault is 100% private. Switch to 'My Private Space' to view.");
        }}
      />

      {/* Modals */}
      <NightlyCheckInModal
        isOpen={isCheckInOpen}
        onClose={() => setIsCheckInOpen(false)}
        onSuccess={refreshDashboard}
      />

      <AddRadarModal
        isOpen={isAddRadarOpen}
        onClose={() => setIsAddRadarOpen(false)}
        onSuccess={refreshDashboard}
        currentMode={currentMode}
        familyId={activeFamily?.id}
      />

      <AddLoanModal
        isOpen={isAddLoanOpen}
        onClose={() => setIsAddLoanOpen(false)}
        onSuccess={refreshDashboard}
      />

      <UPIIntentModal
        bill={selectedUPIBill}
        isOpen={Boolean(selectedUPIBill)}
        onClose={() => setSelectedUPIBill(null)}
        onPaymentReconciled={refreshDashboard}
        currentMode={currentMode}
        familyId={activeFamily?.id}
      />
    </div>
  );
}
