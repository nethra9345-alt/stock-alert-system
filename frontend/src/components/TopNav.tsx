import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Menu,
  Clock,
  User,
  Database,
  ArrowUpRight,
  LogOut,
  LogIn
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { marketApi } from '../services/api';
import { HealthResponse } from '../types';

interface TopNavProps {
  onMenuToggle: () => void;
}

const QUICK_SEARCH_STOCKS = [
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank' },
  { symbol: 'INFY.NS', name: 'Infosys' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors' },
  { symbol: 'SBIN.NS', name: 'State Bank of India' },
];

export const TopNav: React.FC<TopNavProps> = ({ onMenuToggle }) => {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    marketApi.getHealth().then(setHealth).catch(() => null);
  }, []);

  const handleSearchSubmit = (symbol: string) => {
    setIsDropdownOpen(false);
    setSearchQuery('');
    navigate(`/explorer?symbol=${encodeURIComponent(symbol)}`);
  };

  const filteredStocks = QUICK_SEARCH_STOCKS.filter(
    (s) =>
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isMarketOpen = health?.indian_market?.is_open ?? false;

  return (
    <header className="h-16 bg-[#0E131F]/95 backdrop-blur-md border-b border-[#1E293B] sticky top-0 z-30 px-4 lg:px-8 flex items-center justify-between gap-4">
      {/* Mobile Menu & Search */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Search Bar */}
        <div className="relative flex-1">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search Indian stocks (e.g., RELIANCE, TCS, INFY)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsDropdownOpen(true);
              }}
              onFocus={() => setIsDropdownOpen(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchQuery.trim()) {
                  handleSearchSubmit(searchQuery.trim().toUpperCase());
                }
              }}
              className="w-full bg-[#131A2B] border border-slate-700/60 rounded-xl pl-9 pr-4 py-2 text-xs md:text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/30 transition-all font-mono"
            />
          </div>

          {/* Quick Search Dropdown */}
          {isDropdownOpen && searchQuery.length > 0 && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsDropdownOpen(false)}
              />
              <div className="absolute left-0 right-0 top-full mt-2 bg-[#131A2B] border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden divide-y divide-slate-800">
                {filteredStocks.length > 0 ? (
                  filteredStocks.map((s) => (
                    <button
                      key={s.symbol}
                      onClick={() => handleSearchSubmit(s.symbol)}
                      className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-slate-800/80 transition-colors group"
                    >
                      <div>
                        <span className="font-mono text-sm font-semibold text-slate-200 group-hover:text-sky-400">
                          {s.symbol}
                        </span>
                        <p className="text-xs text-slate-400">{s.name}</p>
                      </div>
                      <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-sky-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))
                ) : (
                  <button
                    onClick={() => handleSearchSubmit(searchQuery.toUpperCase())}
                    className="w-full px-4 py-3 text-left text-xs text-sky-400 hover:bg-slate-800/60 font-mono"
                  >
                    Lookup &quot;{searchQuery.toUpperCase()}&quot; in Stock Explorer &rarr;
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Right Action Area */}
      <div className="flex items-center gap-3">
        {/* Market Status Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#141B2D] border border-slate-800 text-xs font-medium">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isMarketOpen ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isMarketOpen ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </span>
          <span className={isMarketOpen ? 'text-emerald-400' : 'text-amber-400 font-mono text-[11px]'}>
            {isMarketOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
          </span>
        </div>

        {/* Database indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#141B2D] border border-slate-800 text-[11px] font-mono text-slate-400">
          <Database className="w-3.5 h-3.5 text-sky-400" />
          <span>{health?.database?.database_type?.toUpperCase() || 'POSTGRESQL'}</span>
        </div>

        {/* IST Clock */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>IST</span>
        </div>

        {/* User Session / Auth Controls */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white font-semibold text-xs shadow-md">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div className="hidden xl:block text-left">
                <div className="text-xs font-semibold text-slate-200">{user.full_name || user.username}</div>
                <div className="text-[10px] text-emerald-400 font-mono">@{user.username}</div>
              </div>
              <button
                onClick={() => logout()}
                title="Sign out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition ml-1"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition"
            >
              <LogIn className="w-3.5 h-3.5" />
              Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopNav;
