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
  ShieldAlert,
  Zap,
  Activity,
  Settings,
  History,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { alertsApi } from '../services/api';
import { PriceAlert, AlertHistoryItem, AlertPreferences } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const PriceAlertsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const prefillSymbol = searchParams.get('symbol') || '';

  const [activeTab, setActiveTab] = useState<'targets' | 'history' | 'preferences'>('targets');

  // State: Price Alerts
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  // State: Alert History
  const [history, setHistory] = useState<AlertHistoryItem[]>([]);
  // State: Alert Preferences
  const [preferences, setPreferences] = useState<AlertPreferences | null>(null);

  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Create Alert Form State
  const [symbol, setSymbol] = useState(prefillSymbol);
  const [targetPrice, setTargetPrice] = useState('');
  const [condition, setCondition] = useState<'ABOVE' | 'BELOW'>('ABOVE');
  const [notes, setNotes] = useState('');
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllAlertData();
  }, []);

  const fetchAllAlertData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [alertsData, histData, prefsData] = await Promise.all([
        alertsApi.getAlerts(),
        alertsApi.getHistory(),
        alertsApi.getPreferences(),
      ]);
      setAlerts(alertsData);
      setHistory(histData);
      setPreferences(prefsData);
    } catch (err: any) {
      console.error('Error fetching alerts data:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load alert system');
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
      setStatusMessage(`Alert created for ${sym} at ₹${price.toFixed(2)}`);
      setTimeout(() => setStatusMessage(null), 4000);
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

  const handleAcknowledge = async (id: number) => {
    try {
      const updated = await alertsApi.acknowledgeAlert(id);
      setHistory((prev) =>
        prev.map((item) => (item.id === id ? updated : item))
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to acknowledge alert');
    }
  };

  const handleResolve = async (id: number) => {
    try {
      const updated = await alertsApi.resolveAlert(id);
      setHistory((prev) =>
        prev.map((item) => (item.id === id ? updated : item))
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to resolve alert');
    }
  };

  const handleEvaluateNow = async () => {
    try {
      setEvaluating(true);
      const res = await alertsApi.evaluateAlerts();
      setStatusMessage(
        `Alert evaluation completed. ${res.new_alerts_triggered_count} new alerts triggered.`
      );
      // Reload history and price alerts
      const [alertsData, histData] = await Promise.all([
        alertsApi.getAlerts(),
        alertsApi.getHistory(),
      ]);
      setAlerts(alertsData);
      setHistory(histData);
      setTimeout(() => setStatusMessage(null), 4500);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to run alert evaluation');
    } finally {
      setEvaluating(false);
    }
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preferences) return;

    try {
      setSavingPrefs(true);
      const updated = await alertsApi.updatePreferences({
        price_alerts_enabled: preferences.price_alerts_enabled,
        portfolio_alerts_enabled: preferences.portfolio_alerts_enabled,
        market_event_alerts_enabled: preferences.market_event_alerts_enabled,
        volume_spike_alerts_enabled: preferences.volume_spike_alerts_enabled,
        min_price_change_pct: preferences.min_price_change_pct,
        portfolio_loss_threshold_pct: preferences.portfolio_loss_threshold_pct,
        portfolio_drawdown_threshold_pct: preferences.portfolio_drawdown_threshold_pct,
        cooldown_minutes: preferences.cooldown_minutes,
      });
      setPreferences(updated);
      setStatusMessage('Smart alert preferences saved successfully.');
      setTimeout(() => setStatusMessage(null), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update preferences');
    } finally {
      setSavingPrefs(false);
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '—';
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  const activeAlertsCount = alerts.filter((a) => a.is_active && !a.is_triggered).length;
  const triggeredAlertsCount = history.filter((h) => h.status === 'TRIGGERED').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Bell className="w-6 h-6 text-amber-400" />
              Smart Alerts & Anomaly Monitor
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              COOLDOWN PROTECTED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time price threshold surveillance, portfolio drawdown safeguards, and market event notifications.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleEvaluateNow}
            disabled={evaluating}
            className="flex items-center gap-2 px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-amber-600/20 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
            <span>{evaluating ? 'Evaluating...' : 'Evaluate Alerts'}</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs font-mono text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={fetchAllAlertData} />}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('targets')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'targets'
              ? 'border-amber-400 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Price Target Alerts ({alerts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'history'
              ? 'border-amber-400 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Triggered Notifications ({history.length})</span>
          {triggeredAlertsCount > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 font-mono">
              {triggeredAlertsCount} Unresolved
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('preferences')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'preferences'
              ? 'border-amber-400 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Settings className="w-4 h-4" />
          <span>Alert Preferences & Cooldown</span>
        </button>
      </div>

      {/* TAB 1: Active Price Target Alerts */}
      {activeTab === 'targets' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Create Alert Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4 h-fit">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Plus className="w-4 h-4 text-amber-400" />
              Set Price Threshold
            </h2>

            {formError && (
              <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-lg font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateAlert} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1.5">Stock Symbol *</label>
                <input
                  type="text"
                  placeholder="e.g. RELIANCE, TCS, INFY"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 uppercase"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1.5">Condition *</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCondition('ABOVE')}
                    className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 border transition ${
                      condition === 'ABOVE'
                        ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-400'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <TrendingUp className="w-3.5 h-3.5" />
                    Above Target
                  </button>
                  <button
                    type="button"
                    onClick={() => setCondition('BELOW')}
                    className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 border transition ${
                      condition === 'BELOW'
                        ? 'bg-rose-950/60 border-rose-500/60 text-rose-400'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <TrendingDown className="w-3.5 h-3.5" />
                    Below Target
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1.5">Target Price (₹) *</label>
                <input
                  type="number"
                  step="any"
                  placeholder="e.g. 3100.00"
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1.5">Trigger Notes (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Take profit target or resistance"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 font-sans"
                />
              </div>

              <button
                type="submit"
                disabled={creating}
                className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Activate Alert'}
              </button>
            </form>
          </div>

          {/* Alerts List */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
              <span>{activeAlertsCount} Active Watchers</span>
              <span>Evaluated against latest quotes</span>
            </div>

            {loading ? (
              <div className="py-12 bg-slate-900 border border-slate-800 rounded-xl">
                <LoadingSpinner text="Loading price targets from PostgreSQL..." />
              </div>
            ) : alerts.length === 0 ? (
              <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-xs">
                No active price alerts. Set a target threshold on the left to begin monitoring.
              </div>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  className={`p-4 bg-slate-900 border rounded-xl shadow-lg transition flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    a.is_triggered
                      ? 'border-amber-500/40 bg-amber-950/10'
                      : a.is_active
                      ? 'border-slate-800 hover:border-slate-700'
                      : 'border-slate-800/40 opacity-60'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-base text-white">{a.symbol}</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                          a.condition === 'ABOVE'
                            ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                            : 'bg-rose-950/60 text-rose-400 border-rose-800/60'
                        }`}
                      >
                        {a.condition === 'ABOVE' ? '▲ ABOVE' : '▼ BELOW'}
                      </span>
                      {a.is_triggered ? (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
                          TRIGGERED
                        </span>
                      ) : a.is_active ? (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-semibold">
                          PAUSED
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                      <span>Target: <strong className="text-white">{formatCurrency(a.target_price)}</strong></span>
                      {a.current_price != null && (
                        <span>Current: <strong className="text-cyan-400">{formatCurrency(a.current_price)}</strong></span>
                      )}
                    </div>

                    {a.notes && (
                      <p className="text-[11px] text-slate-500 font-sans italic pt-0.5">
                        Note: {a.notes}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto">
                    <button
                      onClick={() => handleToggle(a.id)}
                      className={`p-1.5 rounded transition ${
                        a.is_active
                          ? 'text-cyan-400 hover:text-cyan-300'
                          : 'text-slate-600 hover:text-slate-400'
                      }`}
                      title={a.is_active ? 'Pause Alert' : 'Resume Alert'}
                    >
                      {a.is_active ? (
                        <ToggleRight className="w-6 h-6" />
                      ) : (
                        <ToggleLeft className="w-6 h-6" />
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(a.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 rounded transition"
                      title="Delete Alert"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Smart Notifications & History Feed */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
            <span>Notification Ledger ({history.length} records)</span>
            <span>Chronological order with cooldown tracking</span>
          </div>

          {history.length === 0 ? (
            <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-xs">
              No alert notifications logged yet. When price targets, portfolio drawdowns, or market events occur, they will appear here.
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 bg-slate-900 border rounded-xl shadow-lg transition flex flex-col sm:flex-row sm:items-start justify-between gap-4 ${
                    item.status === 'TRIGGERED'
                      ? 'border-amber-500/40 bg-amber-950/10'
                      : 'border-slate-800'
                  }`}
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                          item.severity === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                            : item.severity === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        }`}
                      >
                        {item.alert_type.replace('_', ' ')}
                      </span>

                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                          item.status === 'TRIGGERED'
                            ? 'bg-rose-500/20 text-rose-400'
                            : item.status === 'ACKNOWLEDGED'
                            ? 'bg-cyan-500/20 text-cyan-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {item.status}
                      </span>

                      <span className="text-xs font-mono text-slate-500">
                        {item.created_at ? item.created_at.split('T')[0] : ''}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white font-mono">{item.title}</h4>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">{item.message}</p>

                    <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400 pt-1">
                      {item.trigger_value != null && (
                        <span>Triggered at: <strong className="text-white">{item.trigger_value}</strong></span>
                      )}
                      {item.threshold_value != null && (
                        <span>Threshold: <strong className="text-slate-300">{item.threshold_value}</strong></span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    {item.status === 'TRIGGERED' && (
                      <button
                        onClick={() => handleAcknowledge(item.id)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded-lg text-xs font-mono font-medium transition"
                      >
                        Acknowledge
                      </button>
                    )}
                    {item.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleResolve(item.id)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg text-xs font-mono font-medium transition"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Alert Preferences & Cooldown Controls */}
      {activeTab === 'preferences' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg max-w-2xl space-y-6">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-amber-400" />
              Smart Alert Preferences & Sensitivity
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Configure alert trigger types, drawdown thresholds, and anti-spam cooldown intervals.
            </p>
          </div>

          {preferences && (
            <form onSubmit={handleSavePreferences} className="space-y-5 text-xs font-mono">
              <div className="space-y-3">
                <span className="text-xs uppercase font-semibold text-slate-400 block tracking-wider">
                  Alert Channels & Types
                </span>

                <label className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800 cursor-pointer">
                  <div>
                    <span className="text-white font-semibold block">Price Target Crossings</span>
                    <span className="text-[11px] text-slate-400 font-sans">
                      Notify when individual stock prices break above or below targets
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.price_alerts_enabled}
                    onChange={(e) =>
                      setPreferences({ ...preferences, price_alerts_enabled: e.target.checked })
                    }
                    className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800 cursor-pointer">
                  <div>
                    <span className="text-white font-semibold block">Portfolio Drawdown & Loss Alerts</span>
                    <span className="text-[11px] text-slate-400 font-sans">
                      Safeguard against severe portfolio-level capital drawdowns
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.portfolio_alerts_enabled}
                    onChange={(e) =>
                      setPreferences({ ...preferences, portfolio_alerts_enabled: e.target.checked })
                    }
                    className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800 cursor-pointer">
                  <div>
                    <span className="text-white font-semibold block">Market Anomaly & Event Alerts</span>
                    <span className="text-[11px] text-slate-400 font-sans">
                      Flag extreme price surges, gap downs, and verified news shocks
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.market_event_alerts_enabled}
                    onChange={(e) =>
                      setPreferences({
                        ...preferences,
                        market_event_alerts_enabled: e.target.checked,
                      })
                    }
                    className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800 cursor-pointer">
                  <div>
                    <span className="text-white font-semibold block">Volume Shock Detection</span>
                    <span className="text-[11px] text-slate-400 font-sans">
                      Detect when trading volume exceeds 2x to 5x 20-day moving average
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.volume_spike_alerts_enabled}
                    onChange={(e) =>
                      setPreferences({
                        ...preferences,
                        volume_spike_alerts_enabled: e.target.checked,
                      })
                    }
                    className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                  />
                </label>
              </div>

              <div className="space-y-4 pt-2 border-t border-slate-800">
                <span className="text-xs uppercase font-semibold text-slate-400 block tracking-wider">
                  Numerical Risk Thresholds
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 mb-1">Portfolio Loss Trigger (%)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="1.0"
                      max="50.0"
                      value={preferences.portfolio_loss_threshold_pct}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          portfolio_loss_threshold_pct: parseFloat(e.target.value) || 5.0,
                        })
                      }
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Drawdown Trigger (%)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="2.0"
                      max="50.0"
                      value={preferences.portfolio_drawdown_threshold_pct}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          portfolio_drawdown_threshold_pct: parseFloat(e.target.value) || 8.0,
                        })
                      }
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Min Price Move (%)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="1.0"
                      max="20.0"
                      value={preferences.min_price_change_pct}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          min_price_change_pct: parseFloat(e.target.value) || 4.0,
                        })
                      }
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Cooldown Window (Minutes)</label>
                    <input
                      type="number"
                      step="5"
                      min="5"
                      max="1440"
                      value={preferences.cooldown_minutes}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          cooldown_minutes: parseInt(e.target.value, 10) || 60,
                        })
                      }
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-3">
                <button
                  type="submit"
                  disabled={savingPrefs}
                  className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
                >
                  {savingPrefs ? 'Saving Preferences...' : 'Save Preferences'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
};

export default PriceAlertsPage;
