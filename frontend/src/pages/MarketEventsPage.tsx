import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  ExternalLink,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  RefreshCw,
  BarChart2,
  HelpCircle,
} from 'lucide-react';
import { eventsApi } from '../services/api';
import { MarketEvent } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const MarketEventsPage: React.FC = () => {
  const navigate = useNavigate();

  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Scan input
  const [scanSymbol, setScanSymbol] = useState('RELIANCE.NS');

  // Filters
  const [selectedSymbol, setSelectedSymbol] = useState('ALL');
  const [selectedType, setSelectedType] = useState('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [verifiedOnly, setVerifiedOnly] = useState(false);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await eventsApi.getEvents({ limit: 100 });
      setEvents(res.events);
    } catch (err: any) {
      console.error('Failed to load market events:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch market events');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scanSymbol.trim()) return;

    let sym = scanSymbol.trim().toUpperCase();
    if (!sym.includes('.')) sym += '.NS';

    try {
      setScanning(true);
      setError(null);
      setStatusMessage(`Scanning historical trading sessions for ${sym}...`);

      const res = await eventsApi.analyzeEvents(sym, '6mo');
      setStatusMessage(
        `Analysis complete for ${sym}! ${res.new_events_saved} new events detected (${res.total_events_in_db} total in database).`
      );
      // Reload full list
      await loadEvents();
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (err: any) {
      console.error('Failed to analyze stock:', err);
      setError(err?.response?.data?.detail || err?.message || `Failed to analyze ${sym}`);
    } finally {
      setScanning(false);
    }
  };

  // Filter logic
  const filteredEvents = events.filter((ev) => {
    if (selectedSymbol !== 'ALL' && ev.symbol !== selectedSymbol) return false;
    if (selectedType !== 'ALL' && ev.event_type !== selectedType) return false;
    if (selectedSeverity !== 'ALL' && ev.severity.toLowerCase() !== selectedSeverity.toLowerCase())
      return false;
    if (verifiedOnly && !ev.is_verified) return false;
    return true;
  });

  // Unique symbols for filter dropdown
  const uniqueSymbols = Array.from(new Set(events.map((e) => e.symbol)));

  // Summary statistics
  const totalCount = events.length;
  const extremeCount = events.filter((e) => e.severity === 'extreme').length;
  const highVolumeCount = events.filter((e) => (e.volume_ratio ?? 0) >= 3.0).length;
  const verifiedCount = events.filter((e) => e.is_verified).length;

  const getSeverityBadgeVariant = (severity: string): 'slate' | 'success' | 'warning' | 'danger' | 'info' => {
    switch (severity.toLowerCase()) {
      case 'extreme':
        return 'danger';
      case 'high':
        return 'warning';
      case 'elevated':
        return 'info';
      default:
        return 'slate';
    }
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'Price Surge':
      case 'Gap Up':
      case 'Breakout':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'Price Drop':
      case 'Gap Down':
      case 'Breakdown':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'Volume Spike':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
      case 'High Volatility':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      default:
        return 'text-slate-300 bg-slate-800 border-slate-700';
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString.split('T')[0];
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Market Event Intelligence
                <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-primary-500/20 text-primary-400 border border-primary-500/40">
                  AI EXPLAINER
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Automated detection of abnormal price moves, gap-ups, breakdowns, and volume spikes with verified news catalysts.
              </p>
            </div>
          </div>
        </div>

        {/* Scan & Analyze Action Bar */}
        <form onSubmit={handleScan} className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1.5 rounded-xl">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={scanSymbol}
              onChange={(e) => setScanSymbol(e.target.value)}
              placeholder="e.g. RELIANCE.NS, TCS.NS"
              className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 w-44"
            />
          </div>
          <button
            type="submit"
            disabled={scanning}
            className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            {scanning ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                Scan & Detect
              </>
            )}
          </button>
        </form>
      </div>

      {statusMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs font-mono text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={loadEvents} />}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono uppercase">
            <span>Total Anomalies</span>
            <Activity className="w-4 h-4 text-primary-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">{totalCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Detected across tracked assets</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono uppercase">
            <span>Extreme Moves</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-2">{extremeCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">&gt; 5x volume or major surge</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono uppercase">
            <span>Volume Spikes</span>
            <BarChart2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-2">{highVolumeCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">&ge; 3.0x 20-day rolling average</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono uppercase">
            <span>Verified Catalysts</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">{verifiedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Confirmed with news / reports</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span className="font-semibold uppercase font-mono">Filters:</span>
          </div>

          {/* Symbol Filter */}
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Stocks ({uniqueSymbols.length})</option>
            {uniqueSymbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          {/* Event Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Event Types</option>
            <option value="Price Surge">Price Surge</option>
            <option value="Price Drop">Price Drop</option>
            <option value="Gap Up">Gap Up</option>
            <option value="Gap Down">Gap Down</option>
            <option value="Volume Spike">Volume Spike</option>
            <option value="Breakout">Breakout</option>
            <option value="Breakdown">Breakdown</option>
            <option value="High Volatility">High Volatility</option>
          </select>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Severities</option>
            <option value="extreme">Extreme</option>
            <option value="high">High</option>
            <option value="elevated">Elevated</option>
            <option value="normal">Normal</option>
          </select>

          {/* Verified toggle */}
          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded bg-slate-950 border-slate-800 text-primary-600 focus:ring-0 w-3.5 h-3.5"
            />
            <span>Verified Only</span>
          </label>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Showing <span className="font-bold text-white">{filteredEvents.length}</span> of {events.length} events
        </div>
      </div>

      {/* Events Feed */}
      {loading ? (
        <div className="py-20 flex justify-center">
          <LoadingSpinner text="Loading market event anomalies and AI explanations..." />
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center space-y-3">
          <Zap className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No Market Events Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {events.length === 0
              ? 'No market anomalies have been scanned into the database yet. Click "Scan & Detect" above to analyze RELIANCE.NS or another stock.'
              : 'No events match your current filter criteria. Try resetting filters to view all recorded anomalies.'}
          </p>
          {events.length === 0 && (
            <button
              onClick={() => handleScan({ preventDefault: () => {} } as any)}
              className="mt-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition"
            >
              <Zap className="w-4 h-4" />
              Scan RELIANCE.NS Now
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredEvents.map((ev) => (
            <div
              key={ev.id}
              className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 shadow-lg transition"
            >
              {/* Event Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="font-mono">
                    <span className="text-base font-bold text-white">{ev.symbol}</span>
                    {ev.company_name && (
                      <span className="text-xs text-slate-400 ml-2 hidden sm:inline">
                        • {ev.company_name}
                      </span>
                    )}
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold border ${getEventTypeColor(
                      ev.event_type
                    )}`}
                  >
                    ⚡ {ev.event_type}
                  </span>
                  <Badge variant={getSeverityBadgeVariant(ev.severity)}>
                    {ev.severity.toUpperCase()}
                  </Badge>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{formatDate(ev.event_date)}</span>
                  </div>
                  <button
                    onClick={() => navigate(`/explorer?symbol=${ev.symbol}`)}
                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded text-xs font-medium flex items-center gap-1 transition"
                  >
                    <BarChart2 className="w-3 h-3" />
                    Inspect Chart
                  </button>
                </div>
              </div>

              {/* Metrics Ribbon */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-3 p-3 bg-slate-950/60 rounded-lg border border-slate-800/60 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block text-[11px]">Price Change</span>
                  <span
                    className={`font-bold text-sm ${
                      (ev.price_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {(ev.price_change_pct ?? 0) >= 0 ? '+' : ''}
                    {ev.price_change_pct != null ? `${ev.price_change_pct.toFixed(2)}%` : '—'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px]">Volume Ratio</span>
                  <span className="text-slate-200 font-bold text-sm">
                    {ev.volume_ratio != null ? `${ev.volume_ratio.toFixed(2)}x` : '—'}
                  </span>
                  <span className="text-slate-500 text-[10px] ml-1">vs 20d avg</span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px]">Intraday Range</span>
                  <span className="text-slate-300 font-medium">
                    {ev.intraday_range_pct != null ? `${ev.intraday_range_pct.toFixed(2)}%` : '—'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[11px]">Session Close</span>
                  <span className="text-white font-medium">
                    {ev.close_price != null ? `₹${ev.close_price.toFixed(2)}` : '—'}
                  </span>
                </div>
              </div>

              {/* AI Explanation Body */}
              <div className="space-y-2 mt-3">
                <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                  AI Analysis & Market Catalyst:
                </div>
                <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/40">
                  {ev.explanation_summary}
                </p>
                {ev.explanation_detail && ev.explanation_detail !== ev.explanation_summary && (
                  <p className="text-[11px] text-slate-400 leading-relaxed px-1">
                    {ev.explanation_detail}
                  </p>
                )}
              </div>

              {/* Verified Sources / Unverified Banner */}
              <div className="mt-3 pt-3 border-t border-slate-800/60">
                {ev.is_verified && ev.sources && ev.sources.length > 0 ? (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified Catalyst Sources:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {ev.sources.map((s, sIdx) => (
                        <a
                          key={sIdx}
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800/70 hover:bg-slate-700 border border-slate-700/60 rounded text-[11px] text-slate-300 hover:text-white transition group"
                        >
                          <span className="font-medium truncate max-w-xs">{s.title}</span>
                          <span className="text-slate-500 font-mono text-[10px]">({s.publisher})</span>
                          <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-cyan-400 shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
                    <HelpCircle className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    <span>
                      No verified corporate/news catalyst found within ±4 days. Movement likely driven by broader market sentiment, sector momentum, or institutional positioning.
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MarketEventsPage;
