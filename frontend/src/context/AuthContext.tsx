import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile, AuthTokenResponse } from '../types';
import { authApi, setAccessToken, onTokenChange, refreshAuthToken } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credentials: { username_or_email: string; password: string }) => Promise<void>;
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const saved = localStorage.getItem('stockpulse_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Access token is held strictly in application memory (Stage 12.3 Hardening)
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Synchronize in-memory token state from API refresh and rotation events
  useEffect(() => {
    const unsubscribe = onTokenChange((newToken) => {
      setToken(newToken);
      if (!newToken) {
        setUser(null);
        localStorage.removeItem('stockpulse_user');
      }
    });
    return unsubscribe;
  }, []);

  // Restore session after page reload using existing HttpOnly refresh cookie & CSRF double-submit
  useEffect(() => {
    const verifySession = async () => {
      try {
        // Attempt session restoration via HttpOnly refresh cookie
        await refreshAuthToken();
        const profile = await authApi.getMe();
        setUser(profile);
        localStorage.setItem('stockpulse_user', JSON.stringify(profile));
      } catch {
        // No active or valid session; reset state cleanly
        setAccessToken(null);
        setToken(null);
        setUser(null);
        localStorage.removeItem('stockpulse_user');
        localStorage.removeItem('stockpulse_access_token');
        sessionStorage.removeItem('stockpulse_access_token');
      } finally {
        setLoading(false);
      }
    };

    verifySession();
  }, []);

  const login = async (credentials: { username_or_email: string; password: string }) => {
    const res: AuthTokenResponse = await authApi.login(credentials);
    // Store access token ONLY in memory
    setAccessToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('stockpulse_user', JSON.stringify(res.user));
    // Purge any legacy token storage keys
    localStorage.removeItem('stockpulse_access_token');
    localStorage.removeItem('stockpulse_refresh_token');
    sessionStorage.removeItem('stockpulse_access_token');
  };

  const register = async (data: { email: string; username: string; password: string; full_name?: string }) => {
    const res: AuthTokenResponse = await authApi.register(data);
    // Store access token ONLY in memory
    setAccessToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('stockpulse_user', JSON.stringify(res.user));
    // Purge any legacy token storage keys
    localStorage.removeItem('stockpulse_access_token');
    localStorage.removeItem('stockpulse_refresh_token');
    sessionStorage.removeItem('stockpulse_access_token');
  };

  const logout = () => {
    authApi.logout().catch(() => {});
    setAccessToken(null);
    setToken(null);
    setUser(null);
    localStorage.removeItem('stockpulse_access_token');
    localStorage.removeItem('stockpulse_refresh_token');
    localStorage.removeItem('stockpulse_user');
    sessionStorage.removeItem('stockpulse_access_token');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;

