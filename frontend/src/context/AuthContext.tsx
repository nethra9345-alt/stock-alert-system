import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile, AuthTokenResponse } from '../types';
import { authApi } from '../services/api';

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

  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('stockpulse_access_token');
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifySession = async () => {
      const storedToken = localStorage.getItem('stockpulse_access_token');
      if (storedToken) {
        try {
          const profile = await authApi.getMe();
          setUser(profile);
          localStorage.setItem('stockpulse_user', JSON.stringify(profile));
        } catch (err) {
          console.warn('Session verification failed, clearing expired credentials');
          logout();
        }
      }
      setLoading(false);
    };

    verifySession();
  }, []);

  const login = async (credentials: { username_or_email: string; password: string }) => {
    const res: AuthTokenResponse = await authApi.login(credentials);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('stockpulse_access_token', res.access_token);
    localStorage.setItem('stockpulse_refresh_token', res.refresh_token);
    localStorage.setItem('stockpulse_user', JSON.stringify(res.user));
  };

  const register = async (data: { email: string; username: string; password: string; full_name?: string }) => {
    const res: AuthTokenResponse = await authApi.register(data);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('stockpulse_access_token', res.access_token);
    localStorage.setItem('stockpulse_refresh_token', res.refresh_token);
    localStorage.setItem('stockpulse_user', JSON.stringify(res.user));
  };

  const logout = () => {
    authApi.logout().catch(() => {});
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
