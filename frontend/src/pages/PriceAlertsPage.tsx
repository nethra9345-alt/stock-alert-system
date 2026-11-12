import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Bell,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
  ShieldCheck,
} from 'lucide-react';
import { alertsApi, marketApi } from '../services/api';
import { PriceAlert } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const PriceAlertsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const prefillSymbol = searchParams.get('symbol') || '';

  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Alert Form State
  const [symbol, setSymbol] = useState(prefillSymbol);
  const [targetPrice, setTargetPrice] = useState('');
  const [condition, setCondition] = useState<'ABOVE' | 'BELOW'>('ABOVE');
  const [notes, setNotes] = useState('');
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await alertsApi.getAlerts();
      setAlerts(data);
    } catch (err: any) {
      console.error('Error fetching alerts:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load price alerts');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim() || !targetPrice) {
      setFormError('Please enter valid stock symbol and target price');
      return;
    }

    let sym = symbol.trim().toUpperCase();
    if (!sym.includes('.')) sym += '.NS';

    const price = parseFloat(targetPrice);
    if (isNaN(price) || price <= 0) {
      setFormError('Target price must be a positive number');
      return;
    }

    try {
      setCreating(true);
      setFormError(null);
      const newAlert = await alertsApi.createAlert({
        symbol: sym,
        target_price: price,
        condition,
        notes: notes.trim() || undefined,
      });

      setAlerts((prev) => [newAlert, ...prev]);
      setSymbol('');
      setTargetPrice('');
      setNotes('');
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || 'Failed to create price alert');
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const updated = await alertsApi.toggleAlert(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, is_active: updated.is_active } : a))
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to toggle alert status');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await alertsApi.deleteAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete alert');
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '—';
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Bell className="w-6 h-6 text-amber-400" />
            Price Alerts Engine
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time threshold monitoring with automated alert triggers stored in PostgreSQL.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>PostgreSQL Active Alerts Table</span>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchAlerts} />}

      {/* Create Alert Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Plus className="w-4 h-4 text-cyan-400" />
          Set New Market Price Alert
        </h2>

        {formError && (
          <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg font-mono">
            {formError}
          </div>
        )}

        <form onSubmit={handleCreateAlert} className="grid grid-cols-1 sm:grid-cols-5 gap-3 font-mono text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Symbol *</label>
            <input
              type="text"
              placeholder="e.g. RELIANCE, TCS"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Condition *</label>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value as 'ABOVE' | 'BELOW')}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="ABOVE">Price Rises Above (≥)</option>
              <option value="BELOW">Price Drops Below (≤)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Target Price (₹) *</label>
            <input
              type="number"
              step="any"
              min="0.01"
              placeholder="e.g. 3100.00"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Strategy / Notes</label>
            <input
              type="text"
              placeholder="e.g. Profit taking target"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-sans placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={creating}
              className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-semibold flex items-center justify-center gap-1.5 transition disabled:opacity-50 h-[38px]"
            >
              <Bell className="w-4 h-4" />
              <span>{creating ? 'Saving...' : 'Set Alert'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Alerts Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Active Alerts Roster</h2>
          <span className="text-xs font-mono text-slate-500">
            {alerts.filter((a) => a.is_active).length} Active Monitors
          </span>
        </div>

        {loading ? (
          <div className="py-12">
            <LoadingSpinner text="Querying price alert monitors from PostgreSQL..." />
          </div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <Bell className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-300">No price alerts registered yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Set target price triggers above to automatically monitor stock movements.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                  <th className="py-3 px-4 font-semibold">Instrument</th>
                  <th className="py-3 px-4 font-semibold text-center">Condition</th>
                  <th className="py-3 px-4 font-semibold text-right">Target Price</th>
                  <th className="py-3 px-4 font-semibold text-right">Current Price</th>
                  <th className="py-3 px-4 font-semibold text-center">Status</th>
                  <th className="py-3 px-4 font-semibold">Notes</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {alerts.map((alert) => {
                  return (
                    <tr key={alert.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4 font-bold text-white">
                        <div>{alert.symbol}</div>
                        {alert.company_name && (
                          <div className="text-[11px] font-normal text-slate-400 font-sans">
                            {alert.company_name}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            alert.condition === 'ABOVE'
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                              : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                          }`}
                        >
                          {alert.condition === 'ABOVE' ? 'RISE ≥' : 'FALL ≤'}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right font-bold text-amber-400">
                        {formatCurrency(alert.target_price)}
                      </td>

                      <td className="py-3.5 px-4 text-right text-slate-200">
                        {formatCurrency(alert.current_price)}
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        {alert.is_triggered ? (
                          <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-bold">
                            TRIGGERED
                          </span>
                        ) : alert.is_active ? (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                            PAUSED
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-sans text-slate-400 truncate max-w-xs">
                        {alert.notes || '—'}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggle(alert.id)}
                            className="p-1 text-slate-400 hover:text-cyan-400 transition"
                            title={alert.is_active ? 'Pause Alert' : 'Resume Alert'}
                          >
                            {alert.is_active ? (
                              <ToggleRight className="w-5 h-5 text-emerald-400" />
                            ) : (
                              <ToggleLeft className="w-5 h-5 text-slate-500" />
                            )}
                          </button>
                          <button
                            onClick={() => handleDelete(alert.id)}
                            className="p-1 text-slate-500 hover:text-rose-400 transition"
                            title="Delete Alert"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PriceAlertsPage;

