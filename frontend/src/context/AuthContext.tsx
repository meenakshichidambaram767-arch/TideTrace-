import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserAccount, UserRole } from '../types/api';
import { api } from '../api/endpoints';

interface AuthContextType {
  user: UserAccount | null;
  token: string | null;
  login: (username: string, password?: string) => Promise<void>;
  logout: () => void;
  quickSwitchUser: (username: string) => Promise<void>;
  canReview: boolean;
  canManageRules: boolean;
  canIngest: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SEEDED_PASSWORDS: Record<string, string> = {
  researcher_sam: 'CorrectHorseBatteryStaple!',
  reviewer_alice: 'CorrectHorseBatteryStaple!',
  steward_dave: 'CorrectHorseBatteryStaple!',
  admin_carol: 'CorrectHorseBatteryStaple!',
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserAccount | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('tidetrace_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('tidetrace_user');
    const savedToken = localStorage.getItem('tidetrace_token');
    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser));
        setToken(savedToken);
      } catch {
        localStorage.removeItem('tidetrace_user');
        localStorage.removeItem('tidetrace_token');
      }
    } else {
      // Default auto-login to reviewer_alice for seamless research UX if no session exists
      quickSwitchUser('reviewer_alice').catch(() => {});
    }
    setLoading(false);
  }, []);

  const login = async (username: string, password?: string) => {
    const pass = password || SEEDED_PASSWORDS[username] || 'CorrectHorseBatteryStaple!';
    const res = await api.login(username, pass);
    localStorage.setItem('tidetrace_token', res.access_token);
    localStorage.setItem('tidetrace_user', JSON.stringify(res.user));
    setToken(res.access_token);
    setUser(res.user);
  };

  const quickSwitchUser = async (username: string) => {
    await login(username);
  };

  const logout = () => {
    localStorage.removeItem('tidetrace_token');
    localStorage.removeItem('tidetrace_user');
    setToken(null);
    setUser(null);
  };

  const role: UserRole = user?.role || 'researcher';
  const canReview = ['reviewer', 'steward', 'admin'].includes(role);
  const canManageRules = ['steward', 'admin'].includes(role);
  const canIngest = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        quickSwitchUser,
        canReview,
        canManageRules,
        canIngest,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
