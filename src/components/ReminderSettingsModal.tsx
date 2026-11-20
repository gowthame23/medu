"use client";

import React, { useState } from "react";
import { X, Bell, Sun, Moon, Loader2, Check } from "lucide-react";
import { api, UserProfile } from "@/lib/api";

interface ReminderSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserProfile;
  onUpdated: () => void;
}

export default function ReminderSettingsModal({
  isOpen,
  onClose,
  user,
  onUpdated,
}: ReminderSettingsModalProps) {
  const [morningEnabled, setMorningEnabled] = useState<boolean>(user.reminder_morning_enabled ?? true);
  const [eveningEnabled, setEveningEnabled] = useState<boolean>(user.reminder_evening_enabled ?? true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleToggleMorning = async () => {
    const nextVal = !morningEnabled;
    setMorningEnabled(nextVal);
    await saveSettings(nextVal, eveningEnabled);
  };

  const handleToggleEvening = async () => {
    const nextVal = !eveningEnabled;
    setEveningEnabled(nextVal);
    await saveSettings(morningEnabled, nextVal);
  };

  const saveSettings = async (morning: boolean, evening: boolean) => {
    setIsSaving(true);
    setError(null);
    setSavedSuccess(false);
    try {
      await api.user.updateReminderSettings({
        reminder_morning_enabled: morning,
        reminder_evening_enabled: evening,
      });
      setSavedSuccess(true);
      onUpdated();
      setTimeout(() => setSavedSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update reminder settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-xl border border-stone-200 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-stone-900 leading-tight">Daily Check-in Reminders</h2>
              <p className="text-[10px] text-stone-500">Scheduled in {user.timezone || "Asia/Kolkata"}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-700 rounded-xl hover:bg-stone-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-stone-600 leading-relaxed">
          Calm daily rituals to keep stress away. Reminders appear inside Mend and never contain amounts or liability details.
        </p>

        {error && (
          <div className="p-2.5 rounded-xl bg-rose-50 text-rose-700 text-xs border border-rose-200">
            {error}
          </div>
        )}

        {/* Toggles */}
        <div className="space-y-3 pt-1">
          {/* Morning Toggle */}
          <div className="flex items-center justify-between p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
            <div className="flex items-start gap-2.5 mr-3">
              <Sun className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-bold text-stone-900">Morning Radar (10:00)</div>
                <div className="text-[11px] text-stone-500 leading-tight mt-0.5">
                  Plan your day: check Tomorrow&apos;s Radar and list what is due.
                </div>
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={morningEnabled}
              data-testid="toggle-morning-reminder"
              onClick={handleToggleMorning}
              disabled={isSaving}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                morningEnabled ? "bg-emerald-700" : "bg-stone-300"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                  morningEnabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Evening Toggle */}
          <div className="flex items-center justify-between p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
            <div className="flex items-start gap-2.5 mr-3">
              <Moon className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-bold text-stone-900">Evening Check-in (18:00)</div>
                <div className="text-[11px] text-stone-500 leading-tight mt-0.5">
                  Time for your 30-second check-in: log today&apos;s spending (skipped if already logged).
                </div>
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={eveningEnabled}
              data-testid="toggle-evening-reminder"
              onClick={handleToggleEvening}
              disabled={isSaving}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                eveningEnabled ? "bg-emerald-700" : "bg-stone-300"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                  eveningEnabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between pt-2 text-[11px] text-stone-500">
          <div className="flex items-center gap-1">
            {isSaving ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin text-emerald-700" />
                <span>Saving...</span>
              </>
            ) : savedSuccess ? (
              <>
                <Check className="w-3 h-3 text-emerald-700" />
                <span className="text-emerald-700 font-medium">Preferences updated</span>
              </>
            ) : (
              <span>Updated automatically</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
