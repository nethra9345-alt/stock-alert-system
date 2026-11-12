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
} from 'recharts';
import { OHLCVPoint, IndicatorPoint } from '../types';

interface StockChartProps {
  data: OHLCVPoint[];
  indicators?: IndicatorPoint[];
  symbol: string;
  isPositive?: boolean;
}

export const StockChart: React.FC<StockChartProps> = ({
  data,
  indicators = [],
  symbol,
  isPositive = true,
}) => {
  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(false);
  const [showSMA200, setShowSMA200] = useState(false);
  const [showEMA12, setShowEMA12] = useState(false);
  const [showEMA26, setShowEMA26] = useState(false);
  const [activeSubChart, setActiveSubChart] = useState<'volume' | 'rsi' | 'macd'>('volume');

  // Merge OHLCV data with technical indicators by timestamp index
  const mergedData = data.map((d, i) => {
    const ind = indicators[i] || {};
    return {
      ...d,
      ...ind,
      formattedDate: d.timestamp.includes('T')
        ? d.timestamp.split('T')[0]
        : d.timestamp.split(' ')[0],
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
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
              }}
              formatter={(value: any, name: string) => {
                const numericVal = typeof value === 'number' ? value : parseFloat(value);
                if (name === 'close') return [formatCurrency(numericVal), 'Price'];
                if (name === 'sma_20') return [formatCurrency(numericVal), 'SMA 20'];
                if (name === 'sma_50') return [formatCurrency(numericVal), 'SMA 50'];
                if (name === 'sma_200') return [formatCurrency(numericVal), 'SMA 200'];
                if (name === 'ema_12') return [formatCurrency(numericVal), 'EMA 12'];
                if (name === 'ema_26') return [formatCurrency(numericVal), 'EMA 26'];
                return [value, name];
              }}
              labelStyle={{ color: '#94a3b8', marginBottom: '4px', fontWeight: 600 }}
            />
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
                  formatter={(val: any) => [formatVolume(val), 'Volume']}
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

