import React, { useEffect, useState } from 'react';
import {
  Settings,
  Database,
  Server,
  ShieldCheck,
  CheckCircle2,
  Clock,
  RefreshCw,
  User,
  Info,
} from 'lucide-react';
import { marketApi } from '../services/api';
import { HealthResponse } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await marketApi.getHealth();
      setHealth(data);
    } catch (err: any) {
      console.error('Failed to fetch system diagnostics:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to connect to backend server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Settings className="w-6 h-6 text-cyan-400" />
            System Architecture & Settings
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Backend health diagnostics, PostgreSQL connectivity, and runtime environment parameters.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Ping Diagnostics</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchHealth} />}

      {loading ? (
        <div className="py-16">
          <LoadingSpinner text="Executing live health probe against FastAPI & PostgreSQL..." />
        </div>
      ) : health ? (
        <div className="space-y-6">
          {/* Diagnostics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Database Engine */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">Database Subsystem</h3>
                </div>
                <Badge variant={health.database.status === 'connected' ? 'success' : 'danger'}>
                  {health.database.status.toUpperCase()}
                </Badge>
              </div>

              <div className="space-y-2 text-xs font-mono text-slate-300 pt-2 border-t border-slate-800">
                <div className="flex justify-between">
                  <span className="text-slate-500">Database Engine:</span>
                  <span className="text-cyan-400 font-bold uppercase">
                    {health.database.database_type} 18
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Connectivity:</span>
                  <span className="text-emerald-400 font-semibold">
                    {health.database.connectivity_result}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Driver:</span>
                  <span className="text-white font-semibold">Psycopg 3 (psycopg)</span>
                </div>
                <div className="pt-2">
                  <span className="text-slate-500 block mb-1">Alembic Managed Tables:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {health.database.verified_tables.map((tbl) => (
                      <span
                        key={tbl}
                        className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono"
                      >
                        {tbl}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* FastAPI Backend Diagnostics */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-base font-bold text-white">FastAPI Application Server</h3>
                </div>
                <Badge variant="success">HEALTHY</Badge>
              </div>

              <div className="space-y-2 text-xs font-mono text-slate-300 pt-2 border-t border-slate-800">
                <div className="flex justify-between">
                  <span className="text-slate-500">Service:</span>
                  <span className="text-white font-semibold">{health.service}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Platform Version:</span>
                  <span className="text-cyan-400 font-bold">v{health.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Environment:</span>
                  <span className="text-white uppercase font-semibold">{health.environment}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Current Time (IST):</span>
                  <span className="text-amber-400">{health.current_time_ist}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Market Status:</span>
                  <span
                    className={
                      health.indian_market.is_open ? 'text-emerald-400' : 'text-slate-400'
                    }
                  >
                    {health.indian_market.status_message}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* User Isolation Context */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Active Session & Data Isolation</h3>
              </div>
              <Badge variant="info">USER ID: 1</Badge>
            </div>

            <p className="text-xs text-slate-400">
              StockPulse AI implements multi-tenant user data isolation. Watchlists, portfolio
              transactions, and price alert rules are automatically scoped to the current user ID
              via the <code className="text-cyan-400 font-mono">X-User-Id</code> header.
            </p>
          </div>

          {/* System Architecture Blueprint */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Info className="w-5 h-5 text-cyan-400" />
              StockPulse AI Architecture Stack
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-slate-500 block mb-1">Frontend Layer</span>
                <span className="text-white font-bold block">React 18 + Vite</span>
                <span className="text-slate-400 text-[11px] block mt-1 font-sans">
                  Tailwind CSS, Recharts, Lucide Icons, Axios, React Router v6
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-slate-500 block mb-1">API & ORM Layer</span>
                <span className="text-white font-bold block">Python FastAPI</span>
                <span className="text-slate-400 text-[11px] block mt-1 font-sans">
                  SQLAlchemy 2.0, Alembic Migrations, Pydantic v2 Schemas
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-slate-500 block mb-1">Database & Storage</span>
                <span className="text-white font-bold block">PostgreSQL 18</span>
                <span className="text-slate-400 text-[11px] block mt-1 font-sans">
                  Database: stockpulse, Psycopg 3, SQLite fallback support
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default SettingsPage;

