import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
  PlusCircle,
  Bell,
  Sparkles,
  BarChart2,
  Calendar,
  Layers,
  Info,
  Zap,
  ExternalLink,
  CheckCircle2,
  RefreshCw,
  HelpCircle,
} from 'lucide-react';
import { marketApi, watchlistApi, eventsApi } from '../services/api';
import {
  StockQuote,
  StockHistory,
  TechnicalIndicatorResponse,
  MarketEvent,
} from '../types';
import StockChart from '../components/StockChart';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

const POPULAR_SYMBOLS = [
  'RELIANCE.NS',
  'TCS.NS',
  'INFY.NS',
  'HDFCBANK.NS',
  'ICICIBANK.NS',
  'TATAMOTORS.NS',
  'SBIN.NS',
  'BHARTIARTL.NS',
];

const PERIOD_OPTIONS = [
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
  { label: '2Y', value: '2y' },
];

export const StockExplorerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const currentSymbol = searchParams.get('symbol') || 'RELIANCE.NS';
  const [searchInput, setSearchInput] = useState(currentSymbol);
  const [period, setPeriod] = useState('6mo');

  const [quote, setQuote] = useState<StockQuote | null>(null);
  const [history, setHistory] = useState<StockHistory | null>(null);
  const [indicators, setIndicators] = useState<TechnicalIndicatorResponse | null>(null);
  const [marketEvents, setMarketEvents] = useState<MarketEvent[]>([]);
  const [scanningEvents, setScanningEvents] = useState(false);

  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchStockData(currentSymbol, period);
  }, [currentSymbol, period]);

  const fetchStockData = async (symbol: string, p: string) => {
    try {
      setLoading(true);
      setError(null);

      // Fetch quote, history and indicators in parallel
      const [quoteRes, historyRes, indRes] = await Promise.all([
        marketApi.getStockQuote(symbol),
        marketApi.getStockHistory(symbol, p),
        marketApi.getStockIndicators(symbol, p),
      ]);

      setQuote(quoteRes);
      setHistory(historyRes);
      setIndicators(indRes);

      // Fetch detected market events asynchronously
      try {
        const evRes = await eventsApi.getEventsForSymbol(symbol, { limit: 20 });
        setMarketEvents(evRes.events);
      } catch (evErr) {
        console.warn('Could not fetch events for symbol:', evErr);
        setMarketEvents([]);
      }
    } catch (err: any) {
      console.error('Error fetching stock details:', err);
      setError(err?.response?.data?.detail || err?.message || `Failed to fetch data for ${symbol}`);
    } finally {
      setLoading(false);
    }
  };

  const handleScanEvents = async () => {
    if (!quote) return;
    try {
      setScanningEvents(true);
      const res = await eventsApi.analyzeEvents(quote.symbol, period);
      setToastMessage(
        `Scanned ${quote.symbol}: ${res.new_events_saved} new events detected (${res.total_events_in_db} total recorded).`
      );
      const evRes = await eventsApi.getEventsForSymbol(quote.symbol, { limit: 20 });
      setMarketEvents(evRes.events);
      setTimeout(() => setToastMessage(null), 4000);
    } catch (err: any) {
      console.error('Scan events error:', err);
      setToastMessage(err?.response?.data?.detail || 'Failed to scan market events');
      setTimeout(() => setToastMessage(null), 4000);
    } finally {
      setScanningEvents(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchInput.trim()) return;
    let s = searchInput.trim().toUpperCase();
    if (!s.includes('.')) s += '.NS';
    setSearchParams({ symbol: s });
  };

  const handleSelectSymbol = (sym: string) => {
    setSearchInput(sym);
    setSearchParams({ symbol: sym });
  };

  const handleAddToWatchlist = async () => {
    if (!quote) return;
    try {
      await watchlistApi.addStock(quote.symbol, 'Added from Explorer', quote.name);
      setToastMessage(`Added ${quote.symbol} to your watchlist!`);
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err: any) {
      setToastMessage(err?.response?.data?.detail || 'Failed to add to watchlist');
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '—';
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  const formatLargeNum = (val?: number) => {
    if (!val) return '—';
    if (val >= 1e12) return `₹${(val / 1e12).toFixed(2)} Lakh Cr`;
    if (val >= 1e9) return `₹${(val / 1e9).toFixed(2)} Cr`;
    if (val >= 1e7) return `₹${(val / 1e7).toFixed(2)} Cr`;
    return val.toLocaleString('en-IN');
  };

  const isPositive = quote ? quote.change >= 0 : true;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Search & Presets Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Enter NSE/BSE stock symbol (e.g. INFY, TCS.NS, HDFCBANK)..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-semibold transition"
          >
            Explore
          </button>
        </form>

        <div className="flex items-center gap-2 overflow-x-auto text-xs pb-1 scrollbar-none">
          <span className="text-slate-500 font-mono text-[11px] whitespace-nowrap">Popular:</span>
          {POPULAR_SYMBOLS.map((sym) => (
            <button
              key={sym}
              onClick={() => handleSelectSymbol(sym)}
              className={`px-2.5 py-1 rounded font-mono font-medium transition whitespace-nowrap ${
                currentSymbol === sym
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {sym.replace('.NS', '')}
            </button>
          ))}
        </div>
      </div>

      {toastMessage && (
        <div className="p-3 bg-cyan-950/80 border border-cyan-800 text-cyan-300 text-xs rounded-lg font-mono">
          {toastMessage}
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => fetchStockData(currentSymbol, period)} />}

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <LoadingSpinner text={`Fetching real-time data for ${currentSymbol}...`} />
        </div>
      ) : quote ? (
        <div className="space-y-6">
          {/* Stock Header Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xl font-bold font-mono text-white">{quote.symbol}</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {quote.exchange || 'NSE'}
                </span>
                {quote.is_demo ? (
                  <Badge variant="warning">DEMO / SIMULATED</Badge>
                ) : quote.is_live ? (
                  <Badge variant="success" pulse>LIVE MARKET TICK</Badge>
                ) : quote.data_source === 'cached' ? (
                  <Badge variant="slate">CACHED QUOTE</Badge>
                ) : (
                  <Badge variant="slate">MARKET CLOSED (SETTLED)</Badge>
                )}
              </div>
              <h1 className="text-lg font-semibold text-slate-300">{quote.name}</h1>
              <div className="text-xs text-slate-400 mt-1 font-mono flex flex-wrap items-center gap-2">
                <span>Sector: {quote.sector || 'Equities'}</span>
                <span>•</span>
                <span>
                  Source:{' '}
                  {quote.is_demo
                    ? 'Offline Synthetic Fallback'
                    : quote.data_source === 'live_market'
                    ? 'yfinance (Live Tick)'
                    : quote.data_source === 'cached'
                    ? 'yfinance (Cached Response)'
                    : 'yfinance (EOD Settled)'}
                </span>
                <span>•</span>
                <span>Session: {quote.timestamp}</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center gap-6">
              <div className="text-left md:text-right">
                <div className="text-3xl font-extrabold font-mono text-white">
                  {formatCurrency(quote.price)}
                </div>
                <div
                  className={`flex items-center md:justify-end gap-1 font-mono text-sm font-bold mt-1 ${
                    isPositive ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {isPositive ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )}
                  <span>
                    {isPositive ? '+' : ''}
                    {quote.change.toFixed(2)} ({isPositive ? '+' : ''}
                    {quote.change_percent.toFixed(2)}%)
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 border-t sm:border-t-0 sm:border-l border-slate-800 pt-3 sm:pt-0 sm:pl-6">
                <button
                  onClick={handleAddToWatchlist}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <PlusCircle className="w-3.5 h-3.5 text-cyan-400" />
                  Watchlist
                </button>
                <button
                  onClick={() => navigate(`/alerts?symbol=${quote.symbol}`)}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Bell className="w-3.5 h-3.5 text-amber-400" />
                  Alert
                </button>
                <button
                  onClick={() => navigate(`/insights?symbol=${quote.symbol}`)}
                  className="px-3 py-2 bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Forecast
                </button>
              </div>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">Day High</span>
              <span className="text-white font-bold">{formatCurrency(quote.high)}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">Day Low</span>
              <span className="text-white font-bold">{formatCurrency(quote.low)}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">Prev Close</span>
              <span className="text-white font-bold">{formatCurrency(quote.previous_close)}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">52W High</span>
              <span className="text-slate-300 font-medium">{formatCurrency(quote.fifty_two_week_high)}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">52W Low</span>
              <span className="text-slate-300 font-medium">{formatCurrency(quote.fifty_two_week_low)}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono text-xs">
              <span className="text-slate-500 block">Market Cap</span>
              <span className="text-slate-300 font-medium">{formatLargeNum(quote.market_cap)}</span>
            </div>
          </div>

          {/* Chart Header with Timeframe selector */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Interactive Technical Chart
              </h2>
            </div>

            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setPeriod(opt.value)}
                  className={`px-3 py-1 text-xs font-mono font-medium rounded transition ${
                    period === opt.value
                      ? 'bg-primary-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Recharts Component */}
          {history && history.data.length > 0 ? (
            <StockChart
              data={history.data}
              indicators={indicators?.indicators}
              events={marketEvents}
              symbol={quote.symbol}
              isPositive={isPositive}
            />
          ) : (
            <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
              No historical chart points returned for this timeframe.
            </div>
          )}

          {/* Technical Indicators Summary */}
          {indicators && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">Technical Indicator Signals</h3>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  Calculated using Pandas & NumPy mathematical engines
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-slate-500 font-mono uppercase">RSI (14) Signal</div>
                  <div className="text-xl font-bold font-mono text-white mt-1">
                    {indicators.summary.current_rsi ? indicators.summary.current_rsi.toFixed(2) : '—'}
                  </div>
                  <div className="mt-2 text-xs font-semibold text-cyan-400">
                    {indicators.summary.rsi_signal}
                  </div>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-slate-500 font-mono uppercase">MACD (12,26,9)</div>
                  <div className="text-sm font-bold font-mono text-white mt-2">
                    {indicators.summary.macd_signal}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 font-sans">
                    Moving average momentum convergence
                  </div>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-slate-500 font-mono uppercase">Trend vs SMAs</div>
                  <div className="text-sm font-bold font-mono text-white mt-2">
                    {indicators.summary.trend_sma}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 font-sans">
                    Price relative to 20 & 50 period SMA
                  </div>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <div className="text-xs text-slate-500 font-mono uppercase">Overall Technicals</div>
                  <div
                    className={`text-sm font-bold font-mono mt-2 ${
                      indicators.summary.overall_signal.includes('BULLISH')
                        ? 'text-emerald-400'
                        : indicators.summary.overall_signal.includes('BEARISH')
                        ? 'text-rose-400'
                        : 'text-amber-400'
                    }`}
                  >
                    {indicators.summary.overall_signal}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 font-sans">
                    Combined momentum & trend matrix
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Market Anomalies & AI Explanations Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-400">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Market Event Intelligence & Catalysts
                    <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      {marketEvents.length} Recorded
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Surges, gap moves, and volume spikes detected on historical trading sessions.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleScanEvents}
                  disabled={scanningEvents}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
                >
                  {scanningEvents ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Scanning Sessions...
                    </>
                  ) : (
                    <>
                      <Zap className="w-3.5 h-3.5" />
                      Scan & Detect Anomalies
                    </>
                  )}
                </button>
                <button
                  onClick={() => navigate('/events')}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition"
                >
                  All Market Events →
                </button>
              </div>
            </div>

            {marketEvents.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs font-mono">
                No recorded anomalies for {quote.symbol} yet. Click "Scan & Detect Anomalies" to analyze recent sessions.
              </div>
            ) : (
              <div className="space-y-3">
                {marketEvents.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 hover:border-slate-700 transition"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-semibold text-white">
                          {ev.event_date ? ev.event_date.split('T')[0] : ''}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                            ev.event_type.includes('Surge') || ev.event_type.includes('Up') || ev.event_type.includes('Breakout')
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : ev.event_type.includes('Drop') || ev.event_type.includes('Down') || ev.event_type.includes('Breakdown')
                              ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                              : 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                          }`}
                        >
                          ⚡ {ev.event_type}
                        </span>
                        <Badge
                          variant={
                            ev.severity === 'extreme'
                              ? 'danger'
                              : ev.severity === 'high'
                              ? 'warning'
                              : ev.severity === 'elevated'
                              ? 'info'
                              : 'slate'
                          }
                        >
                          {ev.severity.toUpperCase()}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono">
                        <div>
                          <span className="text-slate-500 mr-1">Move:</span>
                          <span
                            className={`font-bold ${
                              (ev.price_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {(ev.price_change_pct ?? 0) >= 0 ? '+' : ''}
                            {ev.price_change_pct != null ? `${ev.price_change_pct.toFixed(2)}%` : '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 mr-1">Volume:</span>
                          <span className="text-slate-200 font-semibold">
                            {ev.volume_ratio != null ? `${ev.volume_ratio.toFixed(1)}x avg` : '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 mr-1">Close:</span>
                          <span className="text-white">
                            {ev.close_price != null ? `₹${ev.close_price.toFixed(2)}` : '—'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-2.5 space-y-1.5">
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {ev.explanation_summary}
                      </p>
                      {ev.explanation_detail && ev.explanation_detail !== ev.explanation_summary && (
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          {ev.explanation_detail}
                        </p>
                      )}
                    </div>

                    {ev.is_verified && ev.sources && ev.sources.length > 0 ? (
                      <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3 h-3" />
                          Verified Sources:
                        </span>
                        {ev.sources.map((s, idx) => (
                          <a
                            key={idx}
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 hover:text-white transition"
                          >
                            <span className="max-w-[180px] truncate">{s.title}</span>
                            <span className="text-slate-500">({s.publisher})</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
                          </a>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
                        <HelpCircle className="w-3 h-3 text-slate-600" />
                        <span>No verified catalyst in news stream within ±4 days.</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default StockExplorerPage;

