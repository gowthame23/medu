"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, UserProfile, setAccessToken } from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: { email: string; password: string; display_name: string; timezone?: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const profile = await api.auth.getMe();
      setUser(profile);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const initializeAuth = async () => {
      try {
        const token = await api.auth.refresh();
        if (token && isMounted) {
          const profile = await api.auth.getMe();
          if (isMounted) setUser(profile);
        }
      } catch {
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initializeAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    await api.auth.login(email, password);
    await refreshUser();
  };

  const register = async (payload: { email: string; password: string; display_name: string; timezone?: string }) => {
    await api.auth.register(payload);
    await login(payload.email, payload.password);
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
