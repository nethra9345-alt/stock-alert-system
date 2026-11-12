import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Layers,
  Brain,
  Bell,
  Eye,
  ArrowRight,
  ShieldAlert,
  Clock,
  Sparkles,
  BarChart2,
  Zap,
} from 'lucide-react';
import { marketApi, watchlistApi, portfolioApi, mlApi, eventsApi } from '../services/api';
import {
  MarketOverview,
  WatchlistItem,
  PortfolioOverview,
  StockPredictionResponse,
  MarketEvent,
} from '../types';
import IndexCard from '../components/IndexCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [marketData, setMarketData] = useState<MarketOverview | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);
  const [topPrediction, setTopPrediction] = useState<StockPredictionResponse | null>(null);
  const [recentEvents, setRecentEvents] = useState<MarketEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch market overview first
      const overview = await marketApi.getOverview();
      setMarketData(overview);

      // Fetch watchlist and portfolio asynchronously
      try {
        const wl = await watchlistApi.getWatchlist();
        setWatchlist(wl.slice(0, 5));
      } catch (e) {
        console.warn('Watchlist fetch error:', e);
      }

      try {
        const port = await portfolioApi.getPortfolio();
        setPortfolio(port);
      } catch (e) {
        console.warn('Portfolio fetch error:', e);
      }

      try {
        const pred = await mlApi.getPrediction('RELIANCE.NS');
        setTopPrediction(pred);
      } catch (e) {
        console.warn('Prediction fetch error:', e);
      }

      try {
        const evRes = await eventsApi.getEvents({ limit: 4 });
        setRecentEvents(evRes.events);
      } catch (e) {
        console.warn('Events fetch error:', e);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to connect to backend API');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val: number) => {
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  if (loading && !marketData) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner text="Connecting to StockPulse AI Engine & PostgreSQL Database..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800/80 p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs font-mono font-semibold text-cyan-400 tracking-wider uppercase">
              Indian Equity Markets Intelligence
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Market Command Center</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time analytics, technical indicators, and quantitative predictive signals for NSE & BSE.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-slate-800/80 border border-slate-700/60 px-4 py-2 rounded-xl text-right">
            <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>IST (UTC+5:30)</span>
            </div>
            <div className="text-xs font-semibold text-slate-200 mt-0.5">
              {marketData?.current_time_ist || '09:15 - 15:30 IST'}
            </div>
          </div>
          <div
            className={`px-3 py-2 rounded-xl border text-xs font-mono font-bold flex items-center gap-2 ${
              marketData?.market_status === 'OPEN'
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                marketData?.market_status === 'OPEN' ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'
              }`}
            />
            <span>{marketData?.market_status === 'OPEN' ? 'MARKET OPEN' : 'MARKET CLOSED'}</span>
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchDashboardData} />}

      {/* Benchmark Indices Grid */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Key Benchmark Indices
          </h2>
          <span className="text-xs text-slate-500 font-mono">Live NSE / BSE Feed</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketData?.indices?.map((index) => (
            <IndexCard
              key={index.symbol}
              quote={index}
              onClick={() => navigate('/market')}
            />
          ))}
        </div>
      </section>

      {/* Main Grid: Left 2 Cols (Overview & Movers), Right 1 Col (Portfolio & AI) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 span) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top Market Movers */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-primary-400" />
                <h3 className="text-base font-semibold text-white">Top Active Stocks (NIFTY Core)</h3>
              </div>
              <button
                onClick={() => navigate('/market')}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition"
              >
                View All <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400">
                    <th className="pb-3 font-semibold">Symbol</th>
                    <th className="pb-3 font-semibold text-right">Price</th>
                    <th className="pb-3 font-semibold text-right">24h Change</th>
                    <th className="pb-3 font-semibold text-center">Status</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                  {marketData?.top_movers && marketData.top_movers.length > 0 ? (
                    marketData.top_movers.map((stock) => {
                      const isUp = stock.change > 0;
                      return (
                        <tr key={stock.symbol} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 font-semibold text-white">
                            <div>{stock.symbol}</div>
                            <div className="text-[11px] font-normal text-slate-400 font-sans">
                              {stock.name}
                            </div>
                          </td>
                          <td className="py-3 text-right font-medium text-slate-200">
                            {formatCurrency(stock.price)}
                          </td>
                          <td
                            className={`py-3 text-right font-semibold ${
                              isUp ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {isUp ? '+' : ''}
                            {stock.change_percent.toFixed(2)}%
                          </td>
                          <td className="py-3 text-center">
                            {stock.is_demo ? (
                              <Badge variant="warning">DEMO</Badge>
                            ) : (
                              <Badge variant="success">LIVE</Badge>
                            )}
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => navigate(`/explorer?symbol=${stock.symbol}`)}
                              className="px-2.5 py-1 text-xs font-sans font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded transition"
                            >
                              Analyze
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-slate-500">
                        No active stock movers available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quick Watchlist Glance */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-cyan-400" />
                <h3 className="text-base font-semibold text-white">Your Watchlist</h3>
              </div>
              <button
                onClick={() => navigate('/watchlist')}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition"
              >
                Manage Watchlist <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {watchlist.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg">
                <Eye className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs text-slate-400">No stocks in your watchlist yet.</p>
                <button
                  onClick={() => navigate('/watchlist')}
                  className="mt-3 px-3 py-1.5 text-xs font-medium bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition"
                >
                  Add Your First Stock
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {watchlist.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => navigate(`/explorer?symbol=${item.symbol}`)}
                    className="p-3 bg-slate-800/60 hover:bg-slate-800 rounded-lg border border-slate-700/50 cursor-pointer transition flex items-center justify-between"
                  >
                    <div>
                      <div className="font-semibold text-sm text-white font-mono">
                        {item.symbol}
                      </div>
                      <div className="text-xs text-slate-400 truncate max-w-[120px]">
                        {item.company_name || item.notes || item.exchange}
                      </div>
                    </div>
                    <div className="text-right">
                      {item.current_price !== undefined ? (
                        <div className="font-mono text-sm font-semibold text-white">
                          {formatCurrency(item.current_price)}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">Tracked</span>
                      )}
                      {item.change_percent !== undefined && (
                        <div
                          className={`text-xs font-mono font-medium ${
                            item.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {item.change_percent >= 0 ? '+' : ''}
                          {item.change_percent.toFixed(2)}%
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Portfolio & AI Insights */}
        <div className="space-y-6">
          {/* Portfolio Summary Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                <h3 className="text-base font-semibold text-white">Portfolio Valuation</h3>
              </div>
              <button
                onClick={() => navigate('/portfolio')}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition"
              >
                Details <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800/80 mb-4">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Current Value
              </span>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {portfolio ? formatCurrency(portfolio.current_portfolio_value) : '₹0.00'}
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-800 text-xs">
                <div>
                  <span className="text-slate-500">Invested:</span>{' '}
                  <span className="font-mono font-medium text-slate-300">
                    {portfolio ? formatCurrency(portfolio.total_invested) : '₹0.00'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">P&L:</span>{' '}
                  <span
                    className={`font-mono font-bold ${
                      portfolio && portfolio.total_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {portfolio && portfolio.total_pnl >= 0 ? '+' : ''}
                    {portfolio ? formatCurrency(portfolio.total_pnl) : '₹0.00'} (
                    {portfolio ? portfolio.total_pnl_percent.toFixed(2) : '0.00'}%)
                  </span>
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-400 flex items-center justify-between">
              <span>Tracked Holdings:</span>
              <span className="font-mono font-bold text-white">
                {portfolio?.holdings_count || 0} Assets
              </span>
            </div>
          </div>

          {/* AI Signal Spotlight */}
          <div className="bg-gradient-to-b from-slate-900 to-slate-900/90 border border-cyan-900/40 rounded-xl p-5 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />

            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-cyan-400" />
                <h3 className="text-base font-semibold text-white">AI Signal Spotlight</h3>
              </div>
              <Badge variant="info">ENSEMBLE</Badge>
            </div>

            {topPrediction ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-400 font-mono">Benchmark Symbol</span>
                    <div className="text-lg font-bold text-white font-mono">
                      {topPrediction.symbol}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 font-mono">Consensus Direction</span>
                    <div
                      className={`text-sm font-bold font-mono px-2 py-0.5 rounded flex items-center gap-1 justify-end ${
                        topPrediction.consensus_predicted_direction === 'UP'
                          ? 'text-emerald-400 bg-emerald-950/40'
                          : 'text-rose-400 bg-rose-950/40'
                      }`}
                    >
                      {topPrediction.consensus_predicted_direction === 'UP' ? (
                        <TrendingUp className="w-3.5 h-3.5" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5" />
                      )}
                      {topPrediction.consensus_predicted_direction}
                    </div>
                  </div>
                </div>

                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Current Close:</span>
                    <span className="text-white font-medium">
                      {formatCurrency(topPrediction.current_price)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Consensus Target:</span>
                    <span className="text-cyan-400 font-bold">
                      {formatCurrency(topPrediction.consensus_predicted_price)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Confidence:</span>
                    <span className="text-amber-400 font-semibold">
                      {topPrediction.confidence_level}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => navigate(`/insights?symbol=${topPrediction.symbol}`)}
                  className="w-full py-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Explore AI Models & Metrics
                </button>
              </div>
            ) : (
              <div className="p-4 text-center text-xs text-slate-500">
                Loading quantitative forecast...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Market Event Anomaly Radar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Market Event Anomaly Radar</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  AI DETECTED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Automated detection of volume shocks, gap moves, and price spikes with verified news catalysts.
              </p>
            </div>
          </div>

          <button
            onClick={() => navigate('/events')}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition self-start sm:self-auto"
          >
            Explore All Events ({recentEvents.length}) <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentEvents.length === 0 ? (
          <div className="py-6 text-center text-slate-500 text-xs font-mono">
            No market events logged yet. Visit the{' '}
            <button
              onClick={() => navigate('/events')}
              className="text-cyan-400 hover:underline"
            >
              Market Events
            </button>{' '}
            page to scan historical sessions.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {recentEvents.map((ev) => (
              <div
                key={ev.id}
                onClick={() => navigate(`/explorer?symbol=${ev.symbol}`)}
                className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-mono font-bold text-sm text-white group-hover:text-cyan-400 transition">
                      {ev.symbol}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
                        ev.severity === 'extreme'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : ev.severity === 'high'
                          ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}
                    >
                      {ev.severity}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span
                      className={`font-bold ${
                        (ev.price_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {(ev.price_change_pct ?? 0) >= 0 ? '+' : ''}
                      {ev.price_change_pct != null ? `${ev.price_change_pct.toFixed(2)}%` : '—'}
                    </span>
                    <span className="text-slate-400 text-[11px]">
                      Vol: {ev.volume_ratio != null ? `${ev.volume_ratio.toFixed(1)}x` : '—'}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-300 line-clamp-2 leading-snug">
                    {ev.explanation_summary}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>{ev.event_date ? ev.event_date.split('T')[0] : ''}</span>
                  <span className="text-cyan-400 flex items-center gap-0.5 group-hover:underline">
                    Inspect <ArrowRight className="w-2.5 h-2.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Mandatory Financial Disclaimer */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3 text-xs text-slate-400">
        <ShieldAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Financial Risk Disclaimer:</span>{' '}
          StockPulse AI is strictly an experimental educational and analytical platform. All price
          predictions, technical indicators, and quantitative scores are mathematical estimations
          derived from historical OHLCV data. They do not constitute investment advice, financial
          counsel, or guarantees of future market performance. Always conduct independent research
          or consult a SEBI-registered financial advisor before trading.
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

