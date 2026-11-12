import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  PieChart,
  History,
  ShieldCheck,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  X,
} from 'lucide-react';
import { portfolioApi } from '../services/api';
import { PortfolioOverview, PortfolioTransaction } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const PortfolioPage: React.FC = () => {
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);
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
      const [overview, txList] = await Promise.all([
        portfolioApi.getPortfolio(),
        portfolioApi.getTransactions(),
      ]);
      setPortfolio(overview);
      setTransactions(txList);
    } catch (err: any) {
      console.error('Error fetching portfolio:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load portfolio');
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

  const isOverallProfitable = (portfolio?.total_pnl || 0) >= 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Layers className="w-6 h-6 text-cyan-400" />
            Portfolio Management & Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time Indian equity valuation, unrealized P&L calculations, and transaction records.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-primary-600/20 transition self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Transaction</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchPortfolioData} />}

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">
            Total Capital Invested
          </span>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {formatCurrency(portfolio?.total_invested || 0)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Cost basis across all holdings</div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">
            Current Portfolio Value
          </span>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {formatCurrency(portfolio?.current_portfolio_value || 0)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Mark-to-market live valuation</div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">
            Total Unrealized P&L
          </span>
          <div
            className={`text-2xl font-bold font-mono mt-2 flex items-center gap-1.5 ${
              isOverallProfitable ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isOverallProfitable ? (
              <TrendingUp className="w-5 h-5" />
            ) : (
              <TrendingDown className="w-5 h-5" />
            )}
            <span>
              {isOverallProfitable ? '+' : ''}
              {formatCurrency(portfolio?.total_pnl || 0)}
            </span>
          </div>
          <div
            className={`text-xs font-mono font-semibold mt-1 ${
              isOverallProfitable ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isOverallProfitable ? '+' : ''}
            {(portfolio?.total_pnl_percent || 0).toFixed(2)}% overall return
          </div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg">
          <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">
            Active Holdings
          </span>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {portfolio?.holdings_count || 0} Assets
          </div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">
            {transactions.length} Total Transactions
          </div>
        </div>
      </div>

      {/* Holdings Breakdown Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PieChart className="w-4 h-4 text-cyan-400" />
            <h2 className="text-base font-bold text-white">Consolidated Holdings</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Live Mark-to-Market Valuation</span>
        </div>

        {loading ? (
          <div className="py-12">
            <LoadingSpinner text="Computing mark-to-market holdings from PostgreSQL..." />
          </div>
        ) : !portfolio || portfolio.holdings.length === 0 ? (
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
                  <th className="py-3 px-4 font-semibold text-right">Invested</th>
                  <th className="py-3 px-4 font-semibold text-right">Market Price</th>
                  <th className="py-3 px-4 font-semibold text-right">Current Value</th>
                  <th className="py-3 px-4 font-semibold text-right">Unrealized P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {portfolio.holdings.map((h) => {
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
                        <div className="text-[11px]">
                          ({isUp ? '+' : ''}
                          {h.unrealized_pnl_percent.toFixed(2)}%)
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

      {/* Transaction History */}
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
                      {tx.transaction_date.split('T')[0]}
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

      {/* Add Transaction Modal */}
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
                  placeholder="e.g. Tata Consultancy Services"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-sans placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Quantity *</label>
                  <input
                    type="number"
                    step="any"
                    min="1"
                    placeholder="e.g. 50"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Price per Share (₹) *</label>
                  <input
                    type="number"
                    step="any"
                    min="0.01"
                    placeholder="e.g. 2950.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Trade Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Long term accumulation"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-sans placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : 'Record Trade'}
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

