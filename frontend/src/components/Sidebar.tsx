import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  Search,
  Bookmark,
  Briefcase,
  BrainCircuit,
  BellRing,
  Settings,
  Activity,
  Zap,
  X,
  Brain,
  Building2,
  GitCompare,
  FileText,
  Newspaper
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/market', label: 'Market Overview', icon: TrendingUp },
  { to: '/explorer', label: 'Stock Explorer', icon: Search },
  { to: '/news', label: 'News Intelligence', icon: Newspaper },
  { to: '/research', label: 'AI Research', icon: Brain },
  { to: '/fundamentals', label: 'Fundamentals', icon: Building2 },
  { to: '/compare', label: 'Stock Compare', icon: GitCompare },
  { to: '/reports', label: 'Research Reports', icon: FileText },
  { to: '/events', label: 'Market Events', icon: Zap },
  { to: '/watchlist', label: 'Watchlist', icon: Bookmark },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/insights', label: 'AI Insights', icon: BrainCircuit },
  { to: '/alerts', label: 'Price Alerts', icon: BellRing },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#0E131F] border-r border-[#1E293B] flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo and Brand */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-[#1E293B]">
          <NavLink to="/" className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                StockPulse <span className="text-xs px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 font-mono">AI</span>
              </span>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">NSE & BSE Intelligence</p>
            </div>
          </NavLink>

          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm shadow-sky-500/5'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Market Status Footer */}
        <div className="p-4 border-t border-[#1E293B]">
          <div className="p-3 rounded-xl bg-[#141B2D] border border-slate-800/80">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-400 font-medium">India Market</span>
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                IST (UTC+5:30)
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Trading: 09:15 - 15:30</p>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
