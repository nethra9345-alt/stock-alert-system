import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { IndexQuote } from '../types';
import Badge from './Badge';

interface IndexCardProps {
  quote: IndexQuote;
  onClick?: () => void;
}

export const IndexCard: React.FC<IndexCardProps> = ({ quote, onClick }) => {
  const isPositive = quote.change > 0;
  const isNeutral = quote.change === 0;

  const formatPoints = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    }).format(val);
  };

  return (
    <div
      onClick={onClick}
      className={`relative p-5 rounded-xl border border-slate-800 bg-slate-900/80 backdrop-blur-sm 
        hover:border-slate-700 transition-all duration-200 shadow-lg ${
          onClick ? 'cursor-pointer hover:-translate-y-0.5' : ''
        }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-200 tracking-wide">{quote.name}</h3>
            {quote.is_demo && <Badge variant="warning">DEMO</Badge>}
          </div>
          <span className="text-xs font-mono text-slate-500">{quote.symbol}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              quote.is_market_open ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'
            }`}
          />
          <span className="text-slate-400 font-mono text-[11px]">
            {quote.is_market_open ? 'LIVE' : 'CLOSED'}
          </span>
        </div>
      </div>

      <div className="flex items-baseline justify-between mt-2">
        <div className="text-2xl font-bold font-mono tracking-tight text-white">
          {formatPoints(quote.price)}
        </div>
        <div
          className={`flex items-center gap-1 font-mono text-xs font-semibold px-2 py-1 rounded ${
            isNeutral
              ? 'text-slate-400 bg-slate-800'
              : isPositive
              ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900/50'
              : 'text-rose-400 bg-rose-950/40 border border-rose-900/50'
          }`}
        >
          {isNeutral ? (
            <Minus className="w-3.5 h-3.5" />
          ) : isPositive ? (
            <TrendingUp className="w-3.5 h-3.5" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5" />
          )}
          <span>
            {isPositive ? '+' : ''}
            {formatPoints(quote.change)} ({isPositive ? '+' : ''}
            {quote.change_percent.toFixed(2)}%)
          </span>
        </div>
      </div>

      {(quote.high !== undefined || quote.low !== undefined) && (
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div>
            <span className="text-slate-500 mr-1">H:</span>
            <span className="text-slate-300 font-medium">{quote.high ? formatPoints(quote.high) : '—'}</span>
          </div>
          <div>
            <span className="text-slate-500 mr-1">L:</span>
            <span className="text-slate-300 font-medium">{quote.low ? formatPoints(quote.low) : '—'}</span>
          </div>
          <div>
            <span className="text-slate-500 mr-1">P.Close:</span>
            <span className="text-slate-300 font-medium">{quote.previous_close ? formatPoints(quote.previous_close) : '—'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndexCard;

