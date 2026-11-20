"use client";

import React, { useState } from "react";
import { User, Users, LogOut, Bell } from "lucide-react";
import { UserProfile } from "@/lib/api";
import ReminderSettingsModal from "@/components/ReminderSettingsModal";

interface MobileHeaderProps {
  currentMode: "individual" | "family";
  onSwitchMode: (mode: "individual" | "family") => void;
  user: UserProfile | null;
  familyGroupName?: string;
  onLogout: () => void;
  onRefreshUser?: () => void;
}

export default function MobileHeader({
  currentMode,
  onSwitchMode,
  user,
  familyGroupName = "Household Hub",
  onLogout,
  onRefreshUser = () => {},
}: MobileHeaderProps) {
  const [isReminderSettingsOpen, setIsReminderSettingsOpen] = useState(false);

  return (
    <>
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
                {currentMode === "family"
                  ? familyGroupName
                  : `Private Space • ${user?.display_name || "You"}`}
              </div>
            </div>
          </div>

          {/* Profile & Controls */}
          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="text-xs font-bold text-stone-800 leading-none">
                {user?.display_name}
              </div>
              <div className="text-[9px] text-stone-400 font-mono mt-0.5 truncate max-w-[120px]">
                {user?.email}
              </div>
            </div>
            <button
              type="button"
              data-testid="open-reminder-settings-btn"
              onClick={() => setIsReminderSettingsOpen(true)}
              title="Daily check-in reminder settings"
              className="p-1.5 text-stone-500 hover:text-emerald-800 bg-stone-100 hover:bg-stone-200 rounded-xl transition"
            >
              <Bell className="w-4 h-4" />
            </button>
            <button
              onClick={onLogout}
              title="Sign out"
              className="p-1.5 text-stone-400 hover:text-rose-600 bg-stone-100 hover:bg-stone-200 rounded-xl transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* DUAL-ACCOUNT SPACE SWITCHER (Strictly Sandboxed Partition) */}
        <div className="grid grid-cols-2 p-1 bg-stone-200/80 rounded-2xl text-xs font-bold text-stone-600">
          <button
            onClick={() => onSwitchMode("individual")}
            className={`py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              currentMode === "individual"
                ? "bg-white text-stone-900 shadow-xs font-extrabold"
                : "hover:text-stone-900"
            }`}
          >
            <User className="w-3.5 h-3.5 text-stone-600" />
            <span>My Private Space</span>
          </button>

          <button
            onClick={() => onSwitchMode("family")}
            className={`py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              currentMode === "family"
                ? "bg-emerald-800 text-white shadow-xs font-extrabold"
                : "hover:text-stone-900"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Household Hub</span>
          </button>
        </div>
      </header>

      {user && (
        <ReminderSettingsModal
          isOpen={isReminderSettingsOpen}
          onClose={() => setIsReminderSettingsOpen(false)}
          user={user}
          onUpdated={onRefreshUser}
        />
      )}
    </>
  );
}
