import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  PieChart as PieChartIcon,
  History,
  ShieldCheck,
  ShieldAlert,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  X,
  AlertTriangle,
  Activity,
  BarChart2,
  RefreshCw,
  Info,
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { portfolioApi } from '../services/api';
import {
  PortfolioOverview,
  PortfolioTransaction,
  PortfolioAnalytics,
  PortfolioRiskAnalysis,
} from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

const ALLOCATION_COLORS = [
  '#06b6d4', // cyan-500
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#a855f7', // purple-500
  '#ec4899', // pink-500
  '#14b8a6', // teal-500
  '#f97316', // orange-500
];

export const PortfolioPage: React.FC = () => {
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'holdings' | 'risk' | 'allocation'>('holdings');
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [risk, setRisk] = useState<PortfolioRiskAnalysis | null>(null);
  const [transactions, setTransactions] = useState<PortfolioTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [type, setType] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [analyticsData, riskData, txList] = await Promise.all([
        portfolioApi.getAnalytics(),
        portfolioApi.getRisk('6mo'),
        portfolioApi.getTransactions(),
      ]);
      setAnalytics(analyticsData);
      setRisk(riskData);
      setTransactions(txList);
    } catch (err: any) {
      console.error('Error fetching portfolio:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load portfolio intelligence');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim() || !quantity || !price) {
      setFormError('Please enter valid symbol, quantity and price');
      return;
    }

    let sym = symbol.trim().toUpperCase();
    if (!sym.includes('.')) sym += '.NS';

    const qty = parseFloat(quantity);
    const prc = parseFloat(price);

    if (isNaN(qty) || qty <= 0 || isNaN(prc) || prc <= 0) {
      setFormError('Quantity and price must be positive numbers');
      return;
    }

    try {
      setSubmitting(true);
      setFormError(null);

      await portfolioApi.addTransaction({
        symbol: sym,
        company_name: companyName.trim() || undefined,
        transaction_type: type,
        quantity: qty,
        purchase_price: prc,
        notes: notes.trim() || undefined,
      });

      setShowAddModal(false);
      setSymbol('');
      setCompanyName('');
      setQuantity('');
      setPrice('');
      setNotes('');
      // Refresh portfolio
      await fetchPortfolioData();
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || 'Failed to add transaction');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTransaction = async (id: number) => {
    try {
      await portfolioApi.deleteTransaction(id);
      await fetchPortfolioData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete transaction');
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '—';
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  const isOverallProfitable = (analytics?.total_pnl || 0) >= 0;

  // Chart data for asset allocation donut
  const pieData = (analytics?.allocations || []).map((a) => ({
    name: a.symbol,
    value: a.current_value,
    weight: a.weight_pct,
  }));

  // Chart data for stock performance bar chart
  const barData = (analytics?.holdings || [])
    .filter((h) => h.total_quantity > 0)
    .map((h) => ({
      symbol: h.symbol.replace('.NS', ''),
      invested: h.invested_value,
      current: h.current_value,
      unrealized: h.unrealized_pnl,
    }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Layers className="w-6 h-6 text-cyan-400" />
              Portfolio Intelligence & Risk Analytics
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              FIFO ACCOUNTING
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Realized/unrealized P&L accounting, weighted portfolio volatility, drawdown analytics, and NIFTY 50 beta.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-primary-600/20 transition self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Record Trade</span>
          </button>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchPortfolioData} />}

      {/* Top Portfolio Financial KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
            Total Capital Invested
          </span>
          <div className="text-xl font-bold font-mono text-white mt-1.5">
            {formatCurrency(analytics?.total_invested || 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Cost basis of open lots</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
            Current Market Value
          </span>
          <div className="text-xl font-bold font-mono text-white mt-1.5">
            {formatCurrency(analytics?.current_portfolio_value || 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Mark-to-market valuation</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
            Unrealized P&L
          </span>
          <div
            className={`text-xl font-bold font-mono mt-1.5 flex items-center gap-1 ${
              (analytics?.unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(analytics?.unrealized_pnl || 0) >= 0 ? '+' : ''}
            {formatCurrency(analytics?.unrealized_pnl || 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Open holdings gain/loss</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
            Realized P&L
          </span>
          <div
            className={`text-xl font-bold font-mono mt-1.5 ${
              (analytics?.realized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(analytics?.realized_pnl || 0) >= 0 ? '+' : ''}
            {formatCurrency(analytics?.realized_pnl || 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Accumulated closed sales</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
            Overall Return
          </span>
          <div
            className={`text-xl font-bold font-mono mt-1.5 flex items-center gap-1 ${
              isOverallProfitable ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isOverallProfitable ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>
              {isOverallProfitable ? '+' : ''}
              {(analytics?.overall_return_percent || 0).toFixed(2)}%
            </span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            Total Net: {isOverallProfitable ? '+' : ''}
            {formatCurrency(analytics?.total_pnl || 0)}
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('holdings')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'holdings'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <PieChartIcon className="w-4 h-4" />
          <span>Holdings & Ledger</span>
        </button>

        <button
          onClick={() => setActiveTab('risk')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'risk'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Risk & Volatility Intelligence</span>
          {risk && (
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded font-mono uppercase ${
                risk.risk_level === 'LOW_RISK'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : risk.risk_level === 'MODERATE_RISK'
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'bg-rose-500/20 text-rose-400'
              }`}
            >
              {risk.risk_score} Score
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('allocation')}
          className={`pb-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'allocation'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          <span>Asset Allocation & Performance</span>
        </button>
      </div>

      {/* TAB 1: Holdings & Ledger */}
      {activeTab === 'holdings' && (
        <div className="space-y-6">
          {/* Holdings Breakdown Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PieChartIcon className="w-4 h-4 text-cyan-400" />
                <h2 className="text-base font-bold text-white">Consolidated Holdings (FIFO)</h2>
              </div>
              <span className="text-xs font-mono text-slate-500">Live Mark-to-Market Valuation</span>
            </div>

            {loading ? (
              <div className="py-12">
                <LoadingSpinner text="Computing mark-to-market holdings from PostgreSQL..." />
              </div>
            ) : !analytics || analytics.holdings.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No holdings found. Add your first BUY transaction to begin portfolio tracking.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                      <th className="py-3 px-4 font-semibold">Instrument</th>
                      <th className="py-3 px-4 font-semibold text-right">Quantity</th>
                      <th className="py-3 px-4 font-semibold text-right">Avg Buy Price</th>
                      <th className="py-3 px-4 font-semibold text-right">Invested Value</th>
                      <th className="py-3 px-4 font-semibold text-right">Market Price</th>
                      <th className="py-3 px-4 font-semibold text-right">Current Value</th>
                      <th className="py-3 px-4 font-semibold text-right">Unrealized P&L</th>
                      <th className="py-3 px-4 font-semibold text-right">Realized P&L</th>
                      <th className="py-3 px-4 font-semibold text-right">Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    {analytics.holdings.map((h) => {
                      const isUp = h.unrealized_pnl >= 0;
                      return (
                        <tr
                          key={h.symbol}
                          className="hover:bg-slate-800/40 transition cursor-pointer"
                          onClick={() => navigate(`/explorer?symbol=${h.symbol}`)}
                        >
                          <td className="py-3.5 px-4 font-bold text-cyan-400 hover:text-cyan-300">
                            <div>{h.symbol}</div>
                            {h.company_name && (
                              <div className="text-[11px] font-normal text-slate-400 font-sans">
                                {h.company_name}
                              </div>
                            )}
                          </td>

                          <td className="py-3.5 px-4 text-right font-medium text-slate-200">
                            {h.total_quantity.toLocaleString('en-IN')}
                          </td>

                          <td className="py-3.5 px-4 text-right text-slate-300">
                            {formatCurrency(h.avg_buy_price)}
                          </td>

                          <td className="py-3.5 px-4 text-right text-slate-300">
                            {formatCurrency(h.invested_value)}
                          </td>

                          <td className="py-3.5 px-4 text-right font-semibold text-white">
                            {formatCurrency(h.current_price)}
                          </td>

                          <td className="py-3.5 px-4 text-right font-bold text-white">
                            {formatCurrency(h.current_value)}
                          </td>

                          <td
                            className={`py-3.5 px-4 text-right font-bold ${
                              isUp ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            <div>
                              {isUp ? '+' : ''}
                              {formatCurrency(h.unrealized_pnl)}
                            </div>
                            <div className="text-[10px]">
                              ({isUp ? '+' : ''}
                              {h.unrealized_pnl_percent.toFixed(2)}%)
                            </div>
                          </td>

                          <td
                            className={`py-3.5 px-4 text-right font-bold ${
                              h.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {h.realized_pnl !== 0
                              ? `${h.realized_pnl > 0 ? '+' : ''}${formatCurrency(h.realized_pnl)}`
                              : '—'}
                          </td>

                          <td className="py-3.5 px-4 text-right text-slate-300 font-semibold">
                            {h.portfolio_weight_pct > 0 ? `${h.portfolio_weight_pct.toFixed(1)}%` : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Transaction Ledger */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <h2 className="text-base font-bold text-white">Transaction Ledger</h2>
              </div>
              <span className="text-xs font-mono text-slate-500">PostgreSQL Transaction History</span>
            </div>

            {transactions.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs font-sans">
                No transactions recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                      <th className="py-3 px-4 font-semibold">Date</th>
                      <th className="py-3 px-4 font-semibold">Symbol</th>
                      <th className="py-3 px-4 font-semibold text-center">Type</th>
                      <th className="py-3 px-4 font-semibold text-right">Quantity</th>
                      <th className="py-3 px-4 font-semibold text-right">Price</th>
                      <th className="py-3 px-4 font-semibold text-right">Total Amount</th>
                      <th className="py-3 px-4 font-semibold">Notes</th>
                      <th className="py-3 px-4 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    {transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3 px-4 text-slate-400">
                          {tx.transaction_date ? tx.transaction_date.split('T')[0] : '—'}
                        </td>
                        <td className="py-3 px-4 font-bold text-white">{tx.symbol}</td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              tx.transaction_type === 'BUY'
                                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                                : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                            }`}
                          >
                            {tx.transaction_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right text-slate-200">
                          {tx.quantity.toLocaleString('en-IN')}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-200">
                          {formatCurrency(tx.purchase_price)}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-white">
                          {formatCurrency(tx.quantity * tx.purchase_price)}
                        </td>
                        <td className="py-3 px-4 font-sans text-slate-400 truncate max-w-xs">
                          {tx.notes || '—'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleDeleteTransaction(tx.id)}
                            className="p-1.5 text-slate-500 hover:text-rose-400 rounded transition"
                            title="Delete Transaction"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Risk Intelligence & Volatility */}
      {activeTab === 'risk' && (
        <div className="space-y-6">
          {risk ? (
            <>
              {/* Risk Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Composite Risk Score */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                  <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                    <span>Portfolio Risk Score</span>
                    <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-bold font-mono text-white">
                      {risk.risk_score}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">/ 100</span>
                  </div>
                  <div className="mt-2">
                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded uppercase ${
                        risk.risk_level === 'LOW_RISK'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : risk.risk_level === 'MODERATE_RISK'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {risk.risk_level.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Weighted Annualized Volatility */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                  <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                    <span>Annualized Volatility</span>
                    <Activity className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-3xl font-bold font-mono text-white mt-2">
                    {risk.volatility.annualized_portfolio_volatility_pct.toFixed(2)}%
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">Daily: {risk.volatility.daily_portfolio_volatility_pct.toFixed(2)}%</span>
                    <span className="text-amber-400 uppercase font-bold">
                      {risk.volatility.classification.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Maximum Drawdown */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                  <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                    <span>Max Peak-to-Trough</span>
                    <TrendingDown className="w-4 h-4 text-rose-400" />
                  </div>
                  <div className="text-3xl font-bold font-mono text-rose-400 mt-2">
                    -{risk.drawdown.maximum_drawdown_pct.toFixed(2)}%
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-500">
                      {risk.drawdown.peak_date ? `${risk.drawdown.peak_date} → ${risk.drawdown.trough_date}` : 'No drawdown recorded'}
                    </span>
                    <span className="text-rose-400 font-bold uppercase">
                      {risk.drawdown.classification.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Top Holding Concentration & Beta */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                  <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
                    <span>Top Holding / Beta</span>
                    <BarChart2 className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-xl font-bold font-mono text-white mt-2">
                    {risk.concentration.top_holding_symbol || '—'}{' '}
                    <span className="text-sm font-normal text-slate-400">
                      ({risk.concentration.top_holding_weight_pct.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">HHI: {risk.concentration.hhi.toFixed(0)}</span>
                    <span className="text-cyan-400 font-bold">
                      {risk.has_benchmark && risk.benchmark_beta != null
                        ? `β ${risk.benchmark_beta.toFixed(2)} (NIFTY 50)`
                        : 'Beta: N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Stock Volatility Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-base font-bold text-white">Stock-Wise Volatility Breakdown</h3>
                  </div>
                  <span className="text-xs font-mono text-slate-500">
                    Calculated over {risk.sessions_analyzed} aligned sessions
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase bg-slate-950/40">
                        <th className="py-2.5 px-4 font-semibold">Instrument</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Portfolio Weight</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Daily Volatility</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Annualized Volatility</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Relative Risk</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {risk.volatility.stock_volatilities.map((sv) => (
                        <tr key={sv.symbol} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4 font-bold text-white">{sv.symbol}</td>
                          <td className="py-3 px-4 text-right text-slate-300">
                            {sv.weight_pct.toFixed(2)}%
                          </td>
                          <td className="py-3 px-4 text-right text-slate-400">
                            {sv.daily_volatility_pct.toFixed(2)}%
                          </td>
                          <td className="py-3 px-4 text-right font-bold text-cyan-400">
                            {sv.annualized_volatility_pct.toFixed(2)}%
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                sv.annualized_volatility_pct > 25.0
                                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                                  : sv.annualized_volatility_pct > 15.0
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              }`}
                            >
                              {sv.annualized_volatility_pct > 25.0
                                ? 'HIGH'
                                : sv.annualized_volatility_pct > 15.0
                                ? 'MODERATE'
                                : 'LOW'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mathematical Disclaimer */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3 text-xs text-slate-400">
                <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-slate-300">Mathematical Model Disclaimer:</span>{' '}
                  {risk.disclaimer} All volatility, drawdown, and beta metrics are computed using historical daily closing prices. No asset is ever labeled as safe or guaranteed. Past market dynamics do not predict future performance.
                </div>
              </div>
            </>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">
              No risk intelligence data available. Add trade transactions to model portfolio risk.
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Asset Allocation & Performance Charts */}
      {activeTab === 'allocation' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Donut Chart: Asset Allocation */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <PieChartIcon className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">Asset Allocation by Stock</h3>
                </div>
                <span className="text-xs font-mono text-slate-500">Weight % of Total Value</span>
              </div>

              {pieData.length === 0 ? (
                <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                  No active holdings to chart.
                </div>
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={95}
                        paddingAngle={3}
                      >
                        {pieData.map((_, idx) => (
                          <Cell
                            key={`cell-${idx}`}
                            fill={ALLOCATION_COLORS[idx % ALLOCATION_COLORS.length]}
                            stroke="#0f172a"
                            strokeWidth={2}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(val: any, name: string) => [
                          formatCurrency(Number(val)),
                          name,
                        ]}
                      />
                      <Legend
                        verticalAlign="bottom"
                        wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Bar Chart: Invested vs Market Value */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-base font-bold text-white">Cost Basis vs Market Value</h3>
                </div>
                <span className="text-xs font-mono text-slate-500">Comparison in INR</span>
              </div>

              {barData.length === 0 ? (
                <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                  No active holdings to chart.
                </div>
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <XAxis dataKey="symbol" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis
                        stroke="#64748b"
                        fontSize={11}
                        tickLine={false}
                        tickFormatter={(v) => `₹${Math.round(v / 1000)}k`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(val: any) => formatCurrency(Number(val))}
                      />
                      <Legend
                        verticalAlign="top"
                        wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace', paddingBottom: '10px' }}
                      />
                      <Bar dataKey="invested" name="Invested Cost" fill="#64748b" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="current" name="Current Value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Record Trade Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-cyan-400" />
                Record Trade Transaction
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-lg font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleAddTransaction} className="space-y-3 font-mono text-xs">
              <div className="flex gap-2 p-1 bg-slate-950 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setType('BUY')}
                  className={`flex-1 py-1.5 rounded text-xs font-bold transition ${
                    type === 'BUY'
                      ? 'bg-emerald-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setType('SELL')}
                  className={`flex-1 py-1.5 rounded text-xs font-bold transition ${
                    type === 'SELL'
                      ? 'bg-rose-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  SELL
                </button>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Symbol *</label>
                <input
                  type="text"
                  placeholder="e.g. RELIANCE, TCS, INFY"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Company Name</label>
                <input
                  type="text"
                  placeholder="e.g. Reliance Industries Ltd"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Quantity *</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 10"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">
                    {type === 'BUY' ? 'Purchase Price (₹) *' : 'Execution Price (₹) *'}
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 2850.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Trade Notes / Strategy</label>
                <textarea
                  rows={2}
                  placeholder="Optional trade notes..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="pt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-2 bg-primary-600 hover:bg-primary-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
                >
                  {submitting ? 'Recording...' : 'Save Trade'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioPage;
