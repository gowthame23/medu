"use client";

import React, { useState, useEffect } from "react";
import { Sun, Moon, Clock, X, Check } from "lucide-react";
import { api, NotificationItem, UserProfile } from "@/lib/api";

interface ReminderBannerProps {
  user: UserProfile;
  onOpenCheckIn: () => void;
  onReviewRadar: () => void;
  refreshTrigger?: number;
}

export default function ReminderBanner({
  user,
  onOpenCheckIn,
  onReviewRadar,
  refreshTrigger = 0,
}: ReminderBannerProps) {
  const [reminders, setReminders] = useState<NotificationItem[]>([]);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    let isMounted = true;

    async function loadReminders() {
      try {
        const items = await api.notifications.list(10, 0);
        if (isMounted) {
          const activeReminders = items.filter(
            (n) => n.type === "REMINDER" && !n.is_read && !dismissedIds.has(n.id)
          );
          setReminders(activeReminders);
        }
      } catch {
        // Non-intrusive fallback on network failure
      }
    }

    loadReminders();

    return () => {
      isMounted = false;
    };
  }, [user, refreshTrigger, dismissedIds]);

  const handleDismiss = async (notificationId: string) => {
    setDismissedIds((prev) => new Set(prev).add(notificationId));
    setReminders((prev) => prev.filter((r) => r.id !== notificationId));
    try {
      await api.notifications.markRead(notificationId);
    } catch {
      // Ignore background mark read error
    }
  };

  const handleAction = async (reminder: NotificationItem) => {
    await handleDismiss(reminder.id);
    if (reminder.message.includes("Radar")) {
      onReviewRadar();
    } else {
      onOpenCheckIn();
    }
  };

  if (reminders.length === 0) return null;

  const currentReminder = reminders[0];
  const isMorning = currentReminder.message.includes("Radar");

  return (
    <aside
      aria-label="Daily Check-in Reminder"
      data-testid="reminder-banner"
      className="w-full bg-emerald-50 border-b border-emerald-200 px-4 py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs text-emerald-950 transition-all"
    >
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0 text-emerald-800">
          {isMorning ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </div>
        <div>
          <span className="font-bold text-emerald-900 mr-1.5">{currentReminder.title}:</span>
          <span className="text-emerald-800">{currentReminder.message}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
        <button
          type="button"
          data-testid="reminder-action-btn"
          onClick={() => handleAction(currentReminder)}
          className="px-3 py-1 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white font-medium flex items-center gap-1 transition shadow-xs"
        >
          {isMorning ? (
            <>
              <Clock className="w-3.5 h-3.5" />
              <span>Review Radar</span>
            </>
          ) : (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>Check In Now</span>
            </>
          )}
        </button>
        <button
          type="button"
          data-testid="reminder-dismiss-btn"
          onClick={() => handleDismiss(currentReminder.id)}
          title="Dismiss reminder"
          className="p-1 rounded-lg hover:bg-emerald-100 text-emerald-700 transition"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </aside>
  );
}
