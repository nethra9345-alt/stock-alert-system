import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Eye,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  Edit2,
  Check,
  X,
  ExternalLink,
  ShieldCheck,
  Search,
} from 'lucide-react';
import { watchlistApi } from '../services/api';
import { WatchlistItem } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

export const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New stock form
  const [symbolInput, setSymbolInput] = useState('');
  const [nameInput, setNameInput] = useState('');
  const [notesInput, setNotesInput] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [addingError, setAddingError] = useState<string | null>(null);

  // Editing notes
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState('');

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      setError(null);
      const items = await watchlistApi.getWatchlist();
      setWatchlist(items);
    } catch (err: any) {
      console.error('Error fetching watchlist:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load watchlist');
    } finally {
      setLoading(false);
    }
  };

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbolInput.trim()) return;

    let sym = symbolInput.trim().toUpperCase();
    if (!sym.includes('.')) sym += '.NS';

    try {
      setIsAdding(true);
      setAddingError(null);
      const newItem = await watchlistApi.addStock(sym, notesInput.trim() || undefined, nameInput.trim() || undefined);
      setWatchlist((prev) => [newItem, ...prev]);
      setSymbolInput('');
      setNameInput('');
      setNotesInput('');
    } catch (err: any) {
      setAddingError(err?.response?.data?.detail || 'Failed to add symbol to watchlist');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await watchlistApi.removeStock(id);
      setWatchlist((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete watchlist item');
    }
  };

  const startEdit = (item: WatchlistItem) => {
    setEditingId(item.id);
    setEditNotes(item.notes || '');
  };

  const saveEdit = async (item: WatchlistItem) => {
    try {
      const updated = await watchlistApi.updateItem(item.id, editNotes, item.company_name);
      setWatchlist((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, notes: updated.notes } : i))
      );
      setEditingId(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update notes');
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
            <Eye className="w-6 h-6 text-cyan-400" />
            Stock Watchlist
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Persisted in PostgreSQL database with real-time Indian market price tracking.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>PostgreSQL 18 Storage (Isolated Per User)</span>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={fetchWatchlist} />}

      {/* Add Stock Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Plus className="w-4 h-4 text-cyan-400" />
          Add Instrument to Watchlist
        </h2>

        {addingError && (
          <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg font-mono">
            {addingError}
          </div>
        )}

        <form onSubmit={handleAddStock} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Stock Symbol *</label>
            <input
              type="text"
              placeholder="e.g. RELIANCE, TCS, INFY"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Company Name (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Reliance Industries"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Target Strategy / Notes</label>
            <input
              type="text"
              placeholder="e.g. Breakout above 3000"
              value={notesInput}
              onChange={(e) => setNotesInput(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isAdding}
              className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition disabled:opacity-50 h-[38px]"
            >
              <Plus className="w-4 h-4" />
              <span>{isAdding ? 'Adding...' : 'Add to Watchlist'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Watchlist Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
        {loading ? (
          <div className="py-12">
            <LoadingSpinner text="Loading your saved watchlist from PostgreSQL..." />
          </div>
        ) : watchlist.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <Eye className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-300">Your watchlist is currently empty</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Add your favorite NSE and BSE stocks above to monitor real-time prices, indicators, and ML forecasts.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                  <th className="py-3 px-4 font-semibold">Instrument</th>
                  <th className="py-3 px-4 font-semibold">Exchange</th>
                  <th className="py-3 px-4 font-semibold text-right">Price</th>
                  <th className="py-3 px-4 font-semibold text-right">Change</th>
                  <th className="py-3 px-4 font-semibold">Notes / Thesis</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {watchlist.map((item) => {
                  const isUp = (item.change_percent || 0) >= 0;
                  const isEditing = editingId === item.id;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-800/40 transition group"
                    >
                      <td className="py-3.5 px-4 font-bold text-white">
                        <div className="flex items-center gap-2">
                          <span
                            onClick={() => navigate(`/explorer?symbol=${item.symbol}`)}
                            className="text-cyan-400 hover:text-cyan-300 cursor-pointer flex items-center gap-1"
                          >
                            {item.symbol}
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                          </span>
                        </div>
                        {item.company_name && (
                          <div className="text-[11px] font-normal text-slate-400 font-sans">
                            {item.company_name}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 text-[10px]">
                          {item.exchange}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right font-bold text-white">
                        {formatCurrency(item.current_price)}
                      </td>

                      <td
                        className={`py-3.5 px-4 text-right font-semibold ${
                          isUp ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {item.change_percent !== undefined ? (
                          <span className="flex items-center justify-end gap-1">
                            {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                            {isUp ? '+' : ''}
                            {item.change_percent.toFixed(2)}%
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-sans text-slate-300 max-w-xs">
                        {isEditing ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="text"
                              value={editNotes}
                              onChange={(e) => setEditNotes(e.target.value)}
                              className="px-2 py-1 bg-slate-950 border border-cyan-500 rounded text-xs text-white focus:outline-none w-full"
                              autoFocus
                            />
                            <button
                              onClick={() => saveEdit(item)}
                              className="p-1 text-emerald-400 hover:text-emerald-300"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="p-1 text-slate-400 hover:text-slate-300"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between group/note">
                            <span className="truncate text-xs text-slate-400">
                              {item.notes || '—'}
                            </span>
                            <button
                              onClick={() => startEdit(item)}
                              className="opacity-0 group-hover/note:opacity-100 p-1 text-slate-500 hover:text-slate-300 transition"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => navigate(`/explorer?symbol=${item.symbol}`)}
                            className="px-2.5 py-1 text-xs font-sans font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded transition"
                          >
                            Chart
                          </button>
                          <button
                            onClick={() => handleDelete(item.id)}
                            className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded transition"
                            title="Remove from Watchlist"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
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

export default WatchlistPage;

