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
} from 'lucide-react';
import { marketApi, watchlistApi } from '../services/api';
import {
  StockQuote,
  StockHistory,
  TechnicalIndicatorResponse,
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
    } catch (err: any) {
      console.error('Error fetching stock details:', err);
      setError(err?.response?.data?.detail || err?.message || `Failed to fetch data for ${symbol}`);
    } finally {
      setLoading(false);
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
                  <Badge variant="warning">DEMO DATA</Badge>
                ) : (
                  <Badge variant="success">LIVE API FEED</Badge>
                )}
              </div>
              <h1 className="text-lg font-semibold text-slate-300">{quote.name}</h1>
              <div className="text-xs text-slate-500 mt-1 font-mono">
                Sector: {quote.sector || 'Equities'} • Source: {quote.data_source}
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
        </div>
      ) : null}
    </div>
  );
};

export default StockExplorerPage;

