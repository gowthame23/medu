'use client';

import React from 'react';
import { Shield, Flame, Users, User, ChevronDown } from 'lucide-react';

interface MobileHeaderProps {
  currentMode: 'individual' | 'family';
  onSwitchMode: (mode: 'individual' | 'family') => void;
  streak: number;
  userName?: string;
  familyGroupName?: string;
  onOpenAutoDiscover?: () => void;
  activeUser: 'gowtham' | 'priya';
  onSwitchUser: (user: 'gowtham' | 'priya') => void;
}

export default function MobileHeader({
  currentMode,
  onSwitchMode,
  streak,
  userName = 'Gowtham',
  familyGroupName = 'The Ejjurothu Family',
  onOpenAutoDiscover,
  activeUser,
  onSwitchUser,
}: MobileHeaderProps) {
  return (
    <header className="sticky top-0 z-30 bg-[#fafaf7]/95 backdrop-blur-md px-4 pt-3 pb-2.5 border-b border-stone-200/70 space-y-2.5">
      {/* Top Branding & Quick Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-2xl bg-emerald-800 text-white flex items-center justify-center font-black text-sm shadow-xs">
            M
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-extrabold tracking-tight text-stone-900 leading-none">
                Mend
              </span>
              <span className="text-[9px] font-semibold text-emerald-800 bg-emerald-100 px-1.5 py-0.2 rounded">
                Anxiety-Free
              </span>
            </div>
            <div className="text-[10px] text-stone-500 font-medium mt-0.5">
              {currentMode === 'family' ? familyGroupName : `Private Space • ${userName}`}
            </div>
          </div>
        </div>

        {/* User Switcher */}
        <div className="flex items-center gap-1.5">
          {/* Member Toggle */}
          <div className="flex bg-stone-100 p-0.5 rounded-full text-[10px] font-bold border border-stone-200">
            <button
              onClick={() => onSwitchUser('gowtham')}
              className={`px-2.5 py-1 rounded-full transition-all ${
                activeUser === 'gowtham'
                  ? 'bg-white text-stone-900 shadow-2xs font-extrabold'
                  : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              Gowtham
            </button>
            <button
              onClick={() => onSwitchUser('priya')}
              className={`px-2.5 py-1 rounded-full transition-all ${
                activeUser === 'priya'
                  ? 'bg-white text-stone-900 shadow-2xs font-extrabold'
                  : 'text-stone-500 hover:text-stone-800'
              }`}
            >
              Priya
            </button>
          </div>
        </div>
      </div>

      {/* DUAL-ACCOUNT SPACE SWITCHER (Strictly Sandboxed Partition) */}
      <div className="grid grid-cols-2 p-1 bg-stone-200/80 rounded-2xl text-xs font-bold text-stone-600">
        <button
          onClick={() => onSwitchMode('individual')}
          className={`py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
            currentMode === 'individual'
              ? 'bg-white text-stone-900 shadow-xs font-extrabold'
              : 'hover:text-stone-900'
          }`}
        >
          <User className="w-3.5 h-3.5 text-stone-600" />
          <span>My Private Space</span>
        </button>

        <button
          onClick={() => onSwitchMode('family')}
          className={`py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
            currentMode === 'family'
              ? 'bg-emerald-800 text-white shadow-xs font-extrabold'
              : 'hover:text-stone-900'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Family Shared Hub</span>
        </button>
      </div>
    </header>
  );
}
