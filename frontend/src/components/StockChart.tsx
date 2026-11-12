import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import { OHLCVPoint, IndicatorPoint } from '../types';

interface StockChartProps {
  data: OHLCVPoint[];
  indicators?: IndicatorPoint[];
  events?: any[];
  symbol: string;
  isPositive?: boolean;
}

export const StockChart: React.FC<StockChartProps> = ({
  data,
  indicators = [],
  events = [],
  symbol,
  isPositive = true,
}) => {
  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(false);
  const [showSMA200, setShowSMA200] = useState(false);
  const [showEMA12, setShowEMA12] = useState(false);
  const [showEMA26, setShowEMA26] = useState(false);
  const [showEvents, setShowEvents] = useState(true);
  const [activeSubChart, setActiveSubChart] = useState<'volume' | 'rsi' | 'macd'>('volume');

  // Index indicators by normalized date key (YYYY-MM-DD) for exact chronological alignment
  const indicatorByDate = new Map<string, IndicatorPoint>();
  indicators.forEach((ind) => {
    const key = ind.timestamp.includes('T')
      ? ind.timestamp.split('T')[0]
      : ind.timestamp.split(' ')[0];
    indicatorByDate.set(key, ind);
  });

  const eventsByDate = new Map<string, any>();
  events.forEach((ev) => {
    const key = ev.event_date.split('T')[0];
    eventsByDate.set(key, ev);
  });

  const mergedData = data.map((d) => {
    const formattedDate = d.timestamp.includes('T')
      ? d.timestamp.split('T')[0]
      : d.timestamp.split(' ')[0];
    const ind = indicatorByDate.get(formattedDate);
    const ev = eventsByDate.get(formattedDate);

    return {
      timestamp: d.timestamp,
      formattedDate,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close, // Preserve genuine historical close, never overwrite with indicator slice
      volume: d.volume,
      sma_20: ind?.sma_20 ?? null,
      sma_50: ind?.sma_50 ?? null,
      sma_200: ind?.sma_200 ?? null,
      ema_12: ind?.ema_12 ?? null,
      ema_26: ind?.ema_26 ?? null,
      rsi_14: ind?.rsi_14 ?? null,
      macd_line: ind?.macd_line ?? null,
      macd_signal: ind?.macd_signal ?? null,
      macd_histogram: ind?.macd_histogram ?? null,
      marketEvent: ev || null,
    };
  });

  const minPrice = Math.min(...data.map((d) => d.low || d.close)) * 0.98;
  const maxPrice = Math.max(...data.map((d) => d.high || d.close)) * 1.02;

  const strokeColor = isPositive ? '#10b981' : '#f43f5e';
  const fillColor = isPositive ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)';

  const formatCurrency = (val: number) => {
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  const formatVolume = (val: number) => {
    if (val >= 1e7) return `${(val / 1e7).toFixed(2)} Cr`;
    if (val >= 1e5) return `${(val / 1e5).toFixed(2)} L`;
    if (val >= 1e3) return `${(val / 1e3).toFixed(1)}k`;
    return val.toString();
  };

  const formatVolumeDetailed = (val: number) => {
    const formatted = val.toLocaleString('en-IN');
    if (val >= 1e7) return `${formatted} (${(val / 1e7).toFixed(2)} Cr shares)`;
    if (val >= 1e5) return `${formatted} (${(val / 1e5).toFixed(2)} L shares)`;
    return `${formatted} shares`;
  };

  const CustomPriceTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const pt = payload[0].payload;
      const ev = pt.marketEvent;
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl text-xs font-mono max-w-xs z-50">
          <p className="text-slate-400 font-semibold mb-1">{pt.formattedDate}</p>
          <div className="space-y-0.5 mb-1.5">
            <p className="text-slate-200">
              Close: <span className="text-emerald-400 font-bold">{formatCurrency(pt.close)}</span>
            </p>
            {pt.open != null && <p className="text-slate-400">Open: {formatCurrency(pt.open)}</p>}
            {pt.high != null && pt.low != null && (
              <p className="text-slate-400">
                Range: {formatCurrency(pt.low)} – {formatCurrency(pt.high)}
              </p>
            )}
            {pt.volume != null && <p className="text-slate-400">Vol: {formatVolume(pt.volume)}</p>}
          </div>

          {(showSMA20 || showSMA50 || showSMA200 || showEMA12 || showEMA26) && (
            <div className="pt-1.5 border-t border-slate-800 space-y-0.5 text-[11px]">
              {showSMA20 && pt.sma_20 != null && <p className="text-cyan-400">SMA 20: {formatCurrency(pt.sma_20)}</p>}
              {showSMA50 && pt.sma_50 != null && <p className="text-amber-400">SMA 50: {formatCurrency(pt.sma_50)}</p>}
              {showSMA200 && pt.sma_200 != null && <p className="text-purple-400">SMA 200: {formatCurrency(pt.sma_200)}</p>}
              {showEMA12 && pt.ema_12 != null && <p className="text-blue-400">EMA 12: {formatCurrency(pt.ema_12)}</p>}
              {showEMA26 && pt.ema_26 != null && <p className="text-orange-400">EMA 26: {formatCurrency(pt.ema_26)}</p>}
            </div>
          )}

          {ev && showEvents && (
            <div className="mt-2 pt-2 border-t border-slate-800 text-[11px] font-sans">
              <div className="flex items-center gap-1.5 mb-1">
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                    ev.severity === 'extreme'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : ev.severity === 'high'
                      ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  }`}
                >
                  ⚡ {ev.event_type}
                </span>
                <span className="text-[10px] text-slate-400 uppercase font-mono">({ev.severity})</span>
              </div>
              <p className="text-slate-300 text-[11px] leading-snug line-clamp-3">{ev.explanation_summary}</p>
              <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1">
                <span>Move: {ev.price_change_pct != null ? `${ev.price_change_pct > 0 ? '+' : ''}${ev.price_change_pct.toFixed(2)}%` : 'N/A'}</span>
                <span>Vol: {ev.volume_ratio != null ? `${ev.volume_ratio.toFixed(1)}x avg` : 'N/A'}</span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      {/* Chart Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
            Overlays:
          </span>
          <button
            onClick={() => setShowSMA20(!showSMA20)}
            className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition ${
              showSMA20
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            SMA 20
          </button>
          <button
            onClick={() => setShowSMA50(!showSMA50)}
            className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition ${
              showSMA50
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            SMA 50
          </button>
          <button
            onClick={() => setShowSMA200(!showSMA200)}
            className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition ${
              showSMA200
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            SMA 200
          </button>
          <button
            onClick={() => setShowEMA12(!showEMA12)}
            className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition ${
              showEMA12
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            EMA 12
          </button>
          <button
            onClick={() => setShowEMA26(!showEMA26)}
            className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition ${
              showEMA26
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            EMA 26
          </button>
          {events.length > 0 && (
            <button
              onClick={() => setShowEvents(!showEvents)}
              className={`px-2.5 py-1 text-xs font-mono font-medium rounded transition flex items-center gap-1 ${
                showEvents
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <span>⚡ Events ({events.length})</span>
            </button>
          )}
        </div>

        {/* Sub-chart toggle */}
        <div className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700/50">
          <button
            onClick={() => setActiveSubChart('volume')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              activeSubChart === 'volume'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Volume
          </button>
          <button
            onClick={() => setActiveSubChart('rsi')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              activeSubChart === 'rsi'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            RSI (14)
          </button>
          <button
            onClick={() => setActiveSubChart('macd')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              activeSubChart === 'macd'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            MACD (12,26,9)
          </button>
        </div>
      </div>

      {/* Main Price Chart */}
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mergedData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id={`priceGradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.3} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="formattedDate"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              orientation="right"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(v) => `₹${Math.round(v)}`}
            />
            <Tooltip content={<CustomPriceTooltip />} />
            <Area
              type="monotone"
              dataKey="close"
              stroke={strokeColor}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#priceGradient-${symbol})`}
            />
            {showSMA20 && (
              <Line
                type="monotone"
                dataKey="sma_20"
                stroke="#06b6d4"
                strokeWidth={1.5}
                dot={false}
                name="sma_20"
              />
            )}
            {showSMA50 && (
              <Line
                type="monotone"
                dataKey="sma_50"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                name="sma_50"
              />
            )}
            {showSMA200 && (
              <Line
                type="monotone"
                dataKey="sma_200"
                stroke="#a855f7"
                strokeWidth={1.5}
                dot={false}
                name="sma_200"
              />
            )}
            {showEMA12 && (
              <Line
                type="monotone"
                dataKey="ema_12"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
                name="ema_12"
              />
            )}
            {showEMA26 && (
              <Line
                type="monotone"
                dataKey="ema_26"
                stroke="#f97316"
                strokeWidth={1.5}
                dot={false}
                name="ema_26"
              />
            )}
            {showEvents &&
              events.map((ev: any, idx: number) => {
                const dateKey = ev.event_date ? ev.event_date.split('T')[0] : '';
                const matchingPoint = mergedData.find((d) => d.formattedDate === dateKey);
                if (!matchingPoint) return null;
                const dotColor =
                  ev.severity === 'extreme'
                    ? '#ef4444'
                    : ev.severity === 'high'
                    ? '#f97316'
                    : '#f59e0b';
                return (
                  <ReferenceDot
                    key={`ev-dot-${ev.id || idx}`}
                    x={dateKey}
                    y={matchingPoint.close}
                    r={6}
                    fill={dotColor}
                    stroke="#0f172a"
                    strokeWidth={2}
                    isFront={true}
                  />
                );
              })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Sub-chart: Volume / RSI / MACD */}
      <div className="mt-4 pt-3 border-t border-slate-800">
        <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2 px-2">
          <span className="uppercase font-semibold tracking-wider">
            {activeSubChart === 'volume' && 'Trading Volume'}
            {activeSubChart === 'rsi' && 'RSI (14) — Overbought 70 / Oversold 30'}
            {activeSubChart === 'macd' && 'MACD (12, 26, 9) Histogram & Signal'}
          </span>
        </div>

        <div className="h-28 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {activeSubChart === 'volume' ? (
              <ComposedChart data={mergedData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="formattedDate" hide />
                <YAxis
                  orientation="right"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={formatVolume}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    fontSize: '11px',
                  }}
                  formatter={(val: any) => [formatVolumeDetailed(Number(val) || 0), 'Volume']}
                />
                <Bar dataKey="volume" fill="#3b82f6" opacity={0.6} />
              </ComposedChart>
            ) : activeSubChart === 'rsi' ? (
              <ComposedChart data={mergedData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="formattedDate" hide />
                <YAxis
                  domain={[0, 100]}
                  orientation="right"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  ticks={[30, 50, 70]}
                />
                <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="3 3" />
                <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    fontSize: '11px',
                  }}
                  formatter={(val: any) => [
                    typeof val === 'number' ? val.toFixed(2) : val,
                    'RSI',
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="rsi_14"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            ) : (
              <ComposedChart data={mergedData} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="formattedDate" hide />
                <YAxis
                  orientation="right"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                />
                <ReferenceLine y={0} stroke="#64748b" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    fontSize: '11px',
                  }}
                />
                <Bar
                  dataKey="macd_histogram"
                  fill="#38bdf8"
                  opacity={0.8}
                />
                <Line
                  type="monotone"
                  dataKey="macd_line"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  dot={false}
                  name="MACD"
                />
                <Line
                  type="monotone"
                  dataKey="macd_signal"
                  stroke="#f97316"
                  strokeWidth={1.5}
                  dot={false}
                  name="Signal"
                />
              </ComposedChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default StockChart;

