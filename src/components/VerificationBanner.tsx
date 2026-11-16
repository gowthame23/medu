"use client";

import React, { useState } from "react";
import { AlertTriangle, Mail, Phone } from "lucide-react";
import { UserProfile } from "@/lib/api";
import VerificationModal from "@/components/VerificationModal";
import PhoneVerificationModal from "@/components/PhoneVerificationModal";

interface VerificationBannerProps {
  user: UserProfile;
  onRefreshUser: () => void;
}

export default function VerificationBanner({ user, onRefreshUser }: VerificationBannerProps) {
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [isPhoneModalOpen, setIsPhoneModalOpen] = useState(false);

  // If email is already verified, do not render banner
  if (user.email_verified) return null;

  return (
    <>
      <div
        data-testid="verification-banner"
        className="w-full bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-amber-950"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong className="font-semibold">Verify your email:</strong> Complete verification to enable UPI bill payments and settlements.
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            data-testid="verify-email-banner-btn"
            onClick={() => setIsEmailModalOpen(true)}
            className="px-3 py-1 rounded-lg bg-amber-700 hover:bg-amber-800 text-white font-medium flex items-center gap-1 transition shadow-xs"
          >
            <Mail className="w-3.5 h-3.5" />
            <span>Verify email</span>
          </button>
          {!user.phone_verified && (
            <button
              type="button"
              onClick={() => setIsPhoneModalOpen(true)}
              className="px-2.5 py-1 rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-900 font-medium flex items-center gap-1 transition"
            >
              <Phone className="w-3.5 h-3.5 text-amber-700" />
              <span>Verify phone</span>
            </button>
          )}
        </div>
      </div>

      <VerificationModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        userEmail={user.email}
        onVerified={onRefreshUser}
      />

      <PhoneVerificationModal
        isOpen={isPhoneModalOpen}
        onClose={() => setIsPhoneModalOpen(false)}
        currentPhone={user.phone_e164}
        onVerified={onRefreshUser}
      />
    </>
  );
}
