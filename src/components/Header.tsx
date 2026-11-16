'use client';

import React from 'react';
import { Shield, Sparkles, Flame, Moon, ArrowRight, Lock, Eye } from 'lucide-react';

interface HeaderProps {
  activeTab: 'dashboard' | 'vault';
  setActiveTab: (tab: 'dashboard' | 'vault') => void;
  streak: number;
  onOpenCheckIn: () => void;
  isTodayLogged: boolean;
}

export default function Header({
  activeTab,
  setActiveTab,
  streak,
  onOpenCheckIn,
  isTodayLogged,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-stone-50/90 backdrop-blur-md border-b border-stone-200/70 transition-all">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
        {/* Brand & Philosophy */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-emerald-800/10 border border-emerald-800/20 flex items-center justify-center text-emerald-800 shadow-xs">
            <Shield className="w-5 h-5 text-emerald-700" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg tracking-tight text-stone-900">FamilyVault</span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                Kavach
              </span>
            </div>
            <p className="text-xs text-stone-500 hidden sm:block">Once a day, keep the stress away</p>
          </div>
        </div>

        {/* Center / Navigation: Anxiety Shielded Vault Switch */}
        <div className="flex items-center bg-stone-200/60 p-1 rounded-xl text-xs font-medium text-stone-600">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'dashboard'
                ? 'bg-white text-stone-900 shadow-xs font-semibold'
                : 'hover:text-stone-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>Today’s Radar</span>
          </button>

          <button
            onClick={() => setActiveTab('vault')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'vault'
                ? 'bg-white text-stone-900 shadow-xs font-semibold'
                : 'hover:text-stone-900'
            }`}
            title="Liabilities are hidden by default to protect mental peace. Click intentionally to view."
          >
            {activeTab === 'vault' ? (
              <Eye className="w-3.5 h-3.5 text-stone-600" />
            ) : (
              <Lock className="w-3.5 h-3.5 text-stone-400" />
            )}
            <span>Liabilities Vault</span>
            <span className="text-[10px] text-stone-400 font-normal px-1 py-0.2 bg-stone-100 rounded">
              Hidden
            </span>
          </button>
        </div>

        {/* Right Action & Streak Counter */}
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200/70 text-amber-900 text-xs font-medium shadow-2xs"
            title="Consistency brings calm: your nightly 30-second check-in streak!"
          >
            <Flame className="w-4 h-4 text-amber-500 fill-amber-500 animate-pulse" />
            <span className="font-bold">{streak}</span>
            <span className="text-amber-800 hidden md:inline">Day Streak</span>
          </div>

          <button
            onClick={onOpenCheckIn}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shadow-xs ${
              isTodayLogged
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100'
                : 'bg-emerald-800 text-white hover:bg-emerald-900'
            }`}
          >
            <Moon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              {isTodayLogged ? 'Check-in Completed' : 'Nightly Check-in'}
            </span>
            <span className="sm:hidden">{isTodayLogged ? 'Done' : 'Check-in'}</span>
            {!isTodayLogged && <ArrowRight className="w-3 h-3 opacity-80" />}
          </button>
        </div>
      </div>
    </header>
  );
}
