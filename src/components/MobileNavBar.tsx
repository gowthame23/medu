'use client';

import React from 'react';
import { Calendar, Moon, Shield, Lock, Users, Sparkles } from 'lucide-react';

interface MobileNavBarProps {
  currentMode: 'individual' | 'family';
  activeTab: 'dashboard' | 'vault';
  setActiveTab: (tab: 'dashboard' | 'vault') => void;
  onOpenCheckIn: () => void;
  unpaidTomorrowCount: number;
  isTodayLogged: boolean;
  onAttemptVaultInFamilyMode: () => void;
}

export default function MobileNavBar({
  currentMode,
  activeTab,
  setActiveTab,
  onOpenCheckIn,
  unpaidTomorrowCount,
  isTodayLogged,
  onAttemptVaultInFamilyMode,
}: MobileNavBarProps) {
  const handleVaultClick = () => {
    if (currentMode === 'family') {
      onAttemptVaultInFamilyMode();
    } else {
      setActiveTab('vault');
    }
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex justify-center pointer-events-none pb-safe">
      <div className="w-full max-w-md bg-white/95 backdrop-blur-lg border-t border-stone-200/80 px-6 py-2 flex items-center justify-between shadow-lg pointer-events-auto">
        {/* Tab 1: Radar (Tomorrow's Bills & Shared Utilities) */}
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex flex-col items-center gap-1 transition-all py-1 ${
            activeTab === 'dashboard'
              ? 'text-emerald-800 font-bold'
              : 'text-stone-400 hover:text-stone-600 font-medium'
          }`}
        >
          <div className="relative">
            <Calendar className="w-5 h-5" />
            {unpaidTomorrowCount > 0 && (
              <span className="absolute -top-1 -right-2 w-4 h-4 rounded-full bg-amber-500 text-white text-[9px] font-bold flex items-center justify-center">
                {unpaidTomorrowCount}
              </span>
            )}
          </div>
          <span className="text-[10px]">
            {currentMode === 'family' ? 'Family Radar' : 'My Radar'}
          </span>
        </button>

        {/* Center Floating Action Button: 30-Second Check-in (Individual ritual) */}
        <div className="-mt-5">
          <button
            onClick={onOpenCheckIn}
            className={`w-14 h-14 rounded-full shadow-lg flex flex-col items-center justify-center transition-transform active:scale-95 ${
              isTodayLogged
                ? 'bg-emerald-100 text-emerald-800 border-2 border-emerald-500/30'
                : 'bg-emerald-800 text-white shadow-emerald-800/30'
            }`}
            title="30-Second Nightly Check-in"
          >
            <Moon className="w-6 h-6" />
            <span className="text-[8px] font-bold tracking-tight mt-0.5">
              {isTodayLogged ? 'Done ✓' : '30s Log'}
            </span>
          </button>
        </div>

        {/* Tab 2: Liabilities Vault (STRICTLY Individual Only) */}
        <button
          onClick={handleVaultClick}
          className={`flex flex-col items-center gap-1 transition-all py-1 ${
            activeTab === 'vault' && currentMode === 'individual'
              ? 'text-stone-900 font-bold'
              : currentMode === 'family'
              ? 'text-stone-300 opacity-60'
              : 'text-stone-400 hover:text-stone-600 font-medium'
          }`}
          title={
            currentMode === 'family'
              ? 'Personal debt is strictly private and hidden in Family Shared Hub'
              : 'Private Liabilities Vault'
          }
        >
          <div className="relative">
            <Shield className="w-5 h-5" />
            <Lock className="w-2.5 h-2.5 text-stone-400 absolute -bottom-0.5 -right-1" />
          </div>
          <span className="text-[10px]">
            {currentMode === 'family' ? 'Private Vault' : 'My Vault'}
          </span>
        </button>
      </div>
    </nav>
  );
}
