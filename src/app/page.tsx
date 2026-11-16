'use client';

import React, { useState, useEffect } from 'react';
import MobileHeader from '@/components/MobileHeader';
import MobileNavBar from '@/components/MobileNavBar';
import DashboardView from '@/components/DashboardView';
import LiabilitiesVaultView from '@/components/LiabilitiesVaultView';
import NightlyCheckInModal from '@/components/NightlyCheckInModal';
import AddRadarModal from '@/components/AddRadarModal';
import AddLoanModal from '@/components/AddLoanModal';
import UPIIntentModal from '@/components/UPIIntentModal';
import AutoDiscoverModal from '@/components/AutoDiscoverModal';
import { UpcomingRadarRecord, DailyLogRecord, LiabilityRecord, CURRENT_USER, PARTNER_USER, DEFAULT_FAMILY_GROUP } from '@/lib/dataStore';

export default function Home() {
  // Dual-Account Mode: 'individual' (Private Space) vs 'family' (Shared Household Hub)
  const [currentMode, setCurrentMode] = useState<'individual' | 'family'>('individual');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'vault'>('dashboard');
  const [activeUser, setActiveUser] = useState<'gowtham' | 'priya'>('gowtham');

  // Dashboard Data State
  const [streak, setStreak] = useState<number>(14);
  const [isTodayLogged, setIsTodayLogged] = useState<boolean>(false);
  const [todayCheckIn, setTodayCheckIn] = useState<DailyLogRecord | null>(null);
  const [tomorrowRadars, setTomorrowRadars] = useState<UpcomingRadarRecord[]>([]);
  const [allRadars, setAllRadars] = useState<UpcomingRadarRecord[]>([]);
  const [recentLogs, setRecentLogs] = useState<DailyLogRecord[]>([]);
  const [loans, setLoans] = useState<LiabilityRecord[]>([]);
  const [vaultSummary, setVaultSummary] = useState<{
    activeLoansCount: number;
    totalDailyDebtCost: number;
  }>({ activeLoansCount: 0, totalDailyDebtCost: 0 });

  // Modals & 1-Tap UPI Intent State
  const [isCheckInOpen, setIsCheckInOpen] = useState<boolean>(false);
  const [isAddRadarOpen, setIsAddRadarOpen] = useState<boolean>(false);
  const [isAddLoanOpen, setIsAddLoanOpen] = useState<boolean>(false);
  const [isAutoDiscoverOpen, setIsAutoDiscoverOpen] = useState<boolean>(false);
  const [selectedUPIBill, setSelectedUPIBill] = useState<UpcomingRadarRecord | null>(null);
  const [isUPIModalOpen, setIsUPIModalOpen] = useState<boolean>(false);
  const [isAutoSyncing, setIsAutoSyncing] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const activeUserProfile = activeUser === 'gowtham' ? CURRENT_USER : PARTNER_USER;

  // Load Dashboard Data respecting strict dual-account privacy boundary
  const refreshDashboard = async () => {
    try {
      const [dashRes, radarRes, loanRes] = await Promise.all([
        fetch(`/api/dashboard?mode=${currentMode}&userId=${activeUserProfile.id}`),
        fetch(`/api/radar?mode=${currentMode}&userId=${activeUserProfile.id}`),
        // Only query loans in individual mode to ensure zero debt leakage!
        currentMode === 'individual'
          ? fetch(`/api/liabilities?userId=${activeUserProfile.id}`)
          : Promise.resolve({ ok: false, json: () => Promise.resolve([]) } as any),
      ]);

      if (dashRes.ok) {
        const dashData = await dashRes.json();
        setStreak(dashData.streak || 14);
        setIsTodayLogged(dashData.isTodayLogged || false);
        setTodayCheckIn(dashData.todayCheckIn || null);
        setTomorrowRadars(dashData.tomorrowRadars || []);
        setAllRadars(dashData.allRadars || []);
        setRecentLogs(dashData.recentLogs || []);
        if (dashData.vaultOverview) {
          setVaultSummary(dashData.vaultOverview);
        }
      }

      if (radarRes.ok) {
        const radarData = await radarRes.json();
        setAllRadars(radarData.all || []);
      }

      if (loanRes && loanRes.ok) {
        const loanData = await loanRes.json();
        setLoans(loanData.loans || []);
      } else {
        // Enforce empty loans in family mode
        setLoans([]);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }
  };

  useEffect(() => {
    refreshDashboard();

    // Auto-sync every 8 seconds + on window focus
    const interval = setInterval(refreshDashboard, 8000);
    window.addEventListener('focus', refreshDashboard);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', refreshDashboard);
    };
  }, [currentMode, activeUser]);

  // Mode Switching
  const handleSwitchMode = (mode: 'individual' | 'family') => {
    setCurrentMode(mode);
    // If switching to family mode, return to dashboard tab since vault is strictly individual
    if (mode === 'family') {
      setActiveTab('dashboard');
    }
  };

  // Attempting to access vault in family mode
  const handleAttemptVaultInFamilyMode = () => {
    alert(
      '🛡️ Strict Privacy Policy: Personal loans, mortgages, and debts are private individual spaces. Family views cannot access personal liabilities. Switching to My Private Space.'
    );
    setCurrentMode('individual');
    setActiveTab('vault');
  };

  // 1-Tap UPI Intent Trigger
  const handleOpenUPIIntent = (bill: UpcomingRadarRecord) => {
    setSelectedUPIBill(bill);
    setIsUPIModalOpen(true);
  };

  // Quick Toggle Paid
  const handleToggleRadarPaid = async (id: string) => {
    try {
      await fetch(`/api/radar/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paidBy: activeUserProfile.name }),
      });
      refreshDashboard();
    } catch (err) {
      console.error('Failed to toggle bill:', err);
      refreshDashboard();
    }
  };

  // Auto-Sync External Bills
  const handleAutoSyncBills = async () => {
    setIsAutoSyncing(true);
    setSyncMessage(null);
    try {
      const res = await fetch('/api/radar/auto-sync', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSyncMessage(data.message);
        refreshDashboard();
        setTimeout(() => setSyncMessage(null), 5000);
      }
    } catch (err) {
      console.error('Auto-sync error:', err);
    } finally {
      setIsAutoSyncing(false);
    }
  };

  const unpaidTomorrowCount = tomorrowRadars.filter(r => !r.isPaid).length;

  return (
    <div className="min-h-screen flex flex-col justify-between">
      {/* Top Mobile Bar with Mode & User Switcher */}
      <MobileHeader
        currentMode={currentMode}
        onSwitchMode={handleSwitchMode}
        streak={streak}
        userName={activeUserProfile.name.split(' ')[0]}
        familyGroupName={DEFAULT_FAMILY_GROUP.groupName}
        onOpenAutoDiscover={() => setIsAutoDiscoverOpen(true)}
        activeUser={activeUser}
        onSwitchUser={setActiveUser}
      />

      {/* Main Screen View */}
      <main className="flex-1">
        {activeTab === 'dashboard' ? (
          <DashboardView
            currentMode={currentMode}
            streak={streak}
            isTodayLogged={isTodayLogged}
            todayCheckIn={todayCheckIn}
            tomorrowRadars={tomorrowRadars}
            allRadars={allRadars}
            recentLogs={recentLogs}
            onOpenCheckIn={() => setIsCheckInOpen(true)}
            onOpenAddRadar={() => setIsAddRadarOpen(true)}
            onOpenUPIIntentModal={handleOpenUPIIntent}
            onToggleRadarPaid={handleToggleRadarPaid}
            onAutoSyncBills={handleAutoSyncBills}
            onOpenAutoDiscover={() => setIsAutoDiscoverOpen(true)}
            isAutoSyncing={isAutoSyncing}
            syncMessage={syncMessage}
            onNavigateToVault={() => setActiveTab('vault')}
            activeUserName={activeUserProfile.name.split(' ')[0]}
            vaultSummary={vaultSummary}
          />
        ) : (
          <LiabilitiesVaultView
            loans={loans}
            onOpenAddLoan={() => setIsAddLoanOpen(true)}
            onRefreshLoans={refreshDashboard}
            userName={activeUserProfile.name.split(' ')[0]}
          />
        )}
      </main>

      {/* Bottom Navigation Bar */}
      <MobileNavBar
        currentMode={currentMode}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenCheckIn={() => setIsCheckInOpen(true)}
        unpaidTomorrowCount={unpaidTomorrowCount}
        isTodayLogged={isTodayLogged}
        onAttemptVaultInFamilyMode={handleAttemptVaultInFamilyMode}
      />

      {/* 1-Tap UPI Intent Modal (Direct Deep Link to Google Pay / PhonePe with auto-reconcile) */}
      <UPIIntentModal
        bill={selectedUPIBill}
        isOpen={isUPIModalOpen}
        onClose={() => {
          setIsUPIModalOpen(false);
          setSelectedUPIBill(null);
        }}
        onPaymentReconciled={refreshDashboard}
        currentUserName={activeUserProfile.name}
        currentUserId={activeUserProfile.id}
      />

      {/* 30-Second Nightly Check-In Bottom Sheet */}
      <NightlyCheckInModal
        isOpen={isCheckInOpen}
        onClose={() => setIsCheckInOpen(false)}
        onSuccess={refreshDashboard}
        userId={activeUserProfile.id}
        userName={activeUserProfile.name.split(' ')[0]}
      />

      {/* Add Radar Bill Modal */}
      <AddRadarModal
        isOpen={isAddRadarOpen}
        onClose={() => setIsAddRadarOpen(false)}
        onSuccess={refreshDashboard}
        userId={activeUserProfile.id}
      />

      {/* Add Personal Loan Modal */}
      <AddLoanModal
        isOpen={isAddLoanOpen}
        onClose={() => setIsAddLoanOpen(false)}
        onSuccess={refreshDashboard}
        userId={activeUserProfile.id}
      />

      {/* Auto-Discover Household (Phone & Email Integration) */}
      <AutoDiscoverModal
        isOpen={isAutoDiscoverOpen}
        onClose={() => setIsAutoDiscoverOpen(false)}
        onSuccess={refreshDashboard}
      />
    </div>
  );
}
