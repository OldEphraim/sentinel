'use client';
import { createContext, useContext, useState, type ReactNode } from 'react';
import { apiLogin, apiSignup } from '@/lib/api';

interface AuthUser {
  id: string;
  email: string;
}

interface AuthState {
  token: string;
  user: AuthUser;
}

interface AuthContextType {
  auth: AuthState | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, demoKey: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY = 'sentinel_auth';

function readStorage(): AuthState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthState) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => readStorage());

  const login = async (email: string, password: string) => {
    const result = await apiLogin(email, password);
    const state: AuthState = { token: result.token, user: result.user };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    setAuth(state);
  };

  const signup = async (email: string, password: string, demoKey: string) => {
    const result = await apiSignup(email, password, demoKey);
    const state: AuthState = { token: result.token, user: result.user };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    setAuth(state);
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  };

  return (
    <AuthContext.Provider value={{ auth, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
