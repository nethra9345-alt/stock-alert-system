import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Search,
  RefreshCw,
  Clock,
  ShieldCheck,
  ChevronRight,
  Filter,
  PlusCircle,
} from 'lucide-react';
import { marketApi, watchlistApi } from '../services/api';
import { MarketOverview, IndexQuote } from '../types';
import IndexCard from '../components/IndexCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const MarketOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<MarketOverview | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchMarketData();
  }, []);

  const fetchMarketData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await marketApi.getOverview();
      setData(res);
    } catch (err: any) {
      console.error('Error fetching market overview:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch market data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const res = await marketApi.getOverview();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Refresh failed');
    } finally {
      setRefreshing(false);
    }
  };

  const handleAddToWatchlist = async (symbol: string, name: string) => {
    try {
      await watchlistApi.addStock(symbol, `Added from Market Overview`, name);
      setActionMessage(`Added ${symbol} to your watchlist!`);
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || `Failed to add ${symbol}`);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const formatCurrency = (val: number) => {
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  const filteredMovers = data?.top_movers?.filter(
    (item) =>
      item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  if (loading && !data) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner text="Fetching Live NSE/BSE Market Data..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-cyan-400" />
            Indian Equity Markets Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time indices tracking, benchmark performance, and active NSE/BSE volume leaders.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium transition self-start sm:self-auto disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh Quotes'}</span>
        </button>
      </div>

      {actionMessage && (
        <div className="p-3 bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 text-xs rounded-lg font-mono">
          {actionMessage}
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={fetchMarketData} />}

      {/* Market Status Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-sm">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              data?.market_status === 'OPEN'
                ? 'bg-emerald-500 animate-pulse'
                : 'bg-slate-600'
            }`}
          />
          <div>
            <span className="font-semibold text-white">
              {data?.market_status === 'OPEN' ? 'Regular Trading Session Active' : 'Market Closed'}
            </span>
            <span className="text-xs text-slate-400 block font-mono">
              NSE/BSE Trading Hours: Monday - Friday, 09:15 - 15:30 IST
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span>IST Time: <strong className="text-slate-200">{data?.current_time_ist}</strong></span>
          </div>
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Feed: <strong className="text-slate-200">Official yfinance API</strong></span>
          </div>
        </div>
      </div>

      {/* Benchmark Indices Grid */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Major Indices
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data?.indices?.map((idx) => (
            <IndexCard key={idx.symbol} quote={idx} />
          ))}
        </div>
      </section>

      {/* Active Stocks Table */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-white">Active Market Movers (NSE)</h3>
            <p className="text-xs text-slate-400">High-liquidity blue chips tracked by StockPulse AI</p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search symbol or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                <th className="py-3 px-4 font-semibold">Symbol</th>
                <th className="py-3 px-4 font-semibold">Company Name</th>
                <th className="py-3 px-4 font-semibold text-right">Price (INR)</th>
                <th className="py-3 px-4 font-semibold text-right">Net Change</th>
                <th className="py-3 px-4 font-semibold text-right">Change %</th>
                <th className="py-3 px-4 font-semibold text-center">Feed Type</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {filteredMovers.length > 0 ? (
                filteredMovers.map((stock) => {
                  const isUp = stock.change > 0;
                  const isNeutral = stock.change === 0;
                  return (
                    <tr
                      key={stock.symbol}
                      className="hover:bg-slate-800/40 transition group cursor-pointer"
                      onClick={() => navigate(`/explorer?symbol=${stock.symbol}`)}
                    >
                      <td className="py-3.5 px-4 font-bold text-cyan-400 group-hover:text-cyan-300">
                        {stock.symbol}
                      </td>
                      <td className="py-3.5 px-4 font-sans text-slate-300">
                        {stock.name}
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-white">
                        {formatCurrency(stock.price)}
                      </td>
                      <td
                        className={`py-3.5 px-4 text-right font-semibold ${
                          isNeutral ? 'text-slate-400' : isUp ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isUp ? '+' : ''}
                        {stock.change.toFixed(2)}
                      </td>
                      <td
                        className={`py-3.5 px-4 text-right font-semibold ${
                          isNeutral ? 'text-slate-400' : isUp ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isUp ? '+' : ''}
                        {stock.change_percent.toFixed(2)}%
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {stock.is_demo ? (
                          <Badge variant="warning">DEMO</Badge>
                        ) : (
                          <Badge variant="success">LIVE</Badge>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div
                          className="flex items-center justify-end gap-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => handleAddToWatchlist(stock.symbol, stock.name)}
                            title="Add to Watchlist"
                            className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded transition"
                          >
                            <PlusCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => navigate(`/explorer?symbol=${stock.symbol}`)}
                            className="px-2.5 py-1 text-xs font-sans font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded transition flex items-center gap-1"
                          >
                            Chart <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                    No matching stocks found for "{searchQuery}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default MarketOverviewPage;

