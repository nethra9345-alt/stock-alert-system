import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Plus,
  X,
  TrendingUp,
  Activity,
  Layers,
  ArrowRight,
  Info,
  Calendar,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { researchApi } from '../services/api';
import { StockComparison } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const COLOR_PALETTE = ['#38BDF8', '#34D399', '#F472B6', '#FBBF24', '#A78BFA'];

const POPULAR_SUGGESTIONS = [
  'RELIANCE.NS',
  'TCS.NS',
  'INFY.NS',
  'HDFCBANK.NS',
  'ICICIBANK.NS',
  'SBIN.NS',
  'TATAMOTORS.NS',
  'ITC.NS',
  'LT.NS',
];

export const StockComparisonPage: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>(['RELIANCE.NS', 'TCS.NS']);
  const [newSymbolInput, setNewSymbolInput] = useState<string>('');
  const [period, setPeriod] = useState<string>('6mo');
  const [comparison, setComparison] = useState<StockComparison | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComparison = async (symList: string[], timePeriod: string) => {
    if (symList.length < 2) {
      setError('Select at least 2 stocks for comparative analysis.');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await researchApi.compare(symList, timePeriod);
      setComparison(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to compare stocks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison(symbols, period);
  }, [period]);

  const handleAddSymbol = (symToAdd: string) => {
    const sym = symToAdd.trim().toUpperCase();
    if (!sym) return;
    if (symbols.includes(sym)) return;
    if (symbols.length >= 5) {
      setError('Maximum 5 stocks can be compared simultaneously.');
      return;
    }
    const updated = [...symbols, sym];
    setSymbols(updated);
    setNewSymbolInput('');
    fetchComparison(updated, period);
  };

  const handleRemoveSymbol = (symToRemove: string) => {
    if (symbols.length <= 2) {
      setError('At least 2 stocks are required for side-by-side comparison.');
      return;
    }
    const updated = symbols.filter((s) => s !== symToRemove);
    setSymbols(updated);
    fetchComparison(updated, period);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <GitCompare className="w-7 h-7 text-cyan-400" />
            Multi-Stock Comparison Engine
          </h1>
          <p className="text-sm text-slate-400">
            Side-by-side fundamentals, valuation matrix, and normalized historical performance
          </p>
        </div>

        {/* Timeframe Buttons */}
        <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
          {['1mo', '3mo', '6mo', '1y'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition uppercase ${
                period === p
                  ? 'bg-cyan-500 text-slate-950 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Stock Selection & Tag Manager */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 font-medium mr-1">Comparing:</span>
          {symbols.map((sym, idx) => (
            <span
              key={sym}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border shadow-sm"
              style={{
                backgroundColor: `${COLOR_PALETTE[idx % COLOR_PALETTE.length]}15`,
                borderColor: COLOR_PALETTE[idx % COLOR_PALETTE.length],
                color: COLOR_PALETTE[idx % COLOR_PALETTE.length],
              }}
            >
              <span>{sym}</span>
              {symbols.length > 2 && (
                <button
                  onClick={() => handleRemoveSymbol(sym)}
                  className="hover:opacity-75 transition"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </span>
          ))}

          {/* Add Symbol Input */}
          {symbols.length < 5 && (
            <div className="flex items-center gap-1.5 ml-2">
              <input
                type="text"
                value={newSymbolInput}
                onChange={(e) => setNewSymbolInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleAddSymbol(newSymbolInput)}
                placeholder="+ Add ticker (e.g. INFY.NS)"
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 w-44"
              />
              <button
                onClick={() => handleAddSymbol(newSymbolInput)}
                className="p-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Quick Suggestions */}
        <div className="flex items-center gap-2 overflow-x-auto text-[11px] pt-1">
          <span className="text-slate-400 shrink-0">Quick Add:</span>
          {POPULAR_SUGGESTIONS.filter((s) => !symbols.includes(s)).map((s) => (
            <button
              key={s}
              onClick={() => handleAddSymbol(s)}
              className="px-2 py-0.5 rounded bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition"
            >
              + {s}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <LoadingSpinner size="lg" />
        </div>
      ) : comparison ? (
        <div className="space-y-6">
          {/* Normalized Performance Chart */}
          <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-cyan-400">
                <TrendingUp className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">
                  Normalized Price Performance (Rebased to 100)
                </h3>
              </div>
              <span className="text-xs text-slate-400">
                Period: <span className="text-slate-200 font-medium uppercase">{comparison.period}</span>
              </span>
            </div>

            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={comparison.normalized_series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis
                    dataKey="timestamp"
                    stroke="#64748B"
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis
                    stroke="#64748B"
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    domain={['dataMin - 5', 'dataMax + 5']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    labelStyle={{ color: '#94A3B8' }}
                  />
                  <Legend />
                  {comparison.symbols.map((sym, idx) => (
                    <Line
                      key={sym}
                      type="monotone"
                      dataKey={sym}
                      name={sym}
                      stroke={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Objective Algorithmic Summary */}
          {comparison.comparative_summary && comparison.comparative_summary.length > 0 && (
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
              <div className="flex items-center space-x-2 text-cyan-400">
                <Activity className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">Objective Algorithmic Observations</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                {comparison.comparative_summary.map((point, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-900/70 border border-slate-800/80 rounded-lg text-slate-300 leading-relaxed"
                  >
                    {point}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Comparative Metrics Matrix Table */}
          <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center space-x-2 text-cyan-400 border-b border-slate-800 pb-3">
              <Layers className="w-5 h-5" />
              <h3 className="font-semibold text-slate-100">Fundamental & Valuation Multiples Matrix</h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4 font-semibold">Category</th>
                    <th className="py-3 px-4 font-semibold">Financial Metric</th>
                    <th className="py-3 px-4 font-semibold text-center">Unit</th>
                    {comparison.symbols.map((sym, idx) => (
                      <th
                        key={sym}
                        className="py-3 px-4 font-semibold text-right"
                        style={{ color: COLOR_PALETTE[idx % COLOR_PALETTE.length] }}
                      >
                        {sym}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {comparison.metrics_matrix.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/40 transition">
                      <td className="py-2.5 px-4 text-xs font-semibold text-slate-400">
                        {row.category}
                      </td>
                      <td className="py-2.5 px-4 font-medium text-slate-200">{row.metric}</td>
                      <td className="py-2.5 px-4 text-xs text-center text-slate-400">{row.unit}</td>
                      {comparison.symbols.map((sym) => {
                        const val = row.values[sym];
                        return (
                          <td key={sym} className="py-2.5 px-4 text-right font-medium text-slate-100">
                            {val !== null && val !== undefined ? (
                              row.metric === 'Market Cap' ? (
                                `₹${(val / 1e12).toFixed(2)}T`
                              ) : typeof val === 'number' ? (
                                val.toFixed(2)
                              ) : (
                                String(val)
                              )
                            ) : (
                              <span className="text-slate-400 italic">UNAVAILABLE</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default StockComparisonPage;

