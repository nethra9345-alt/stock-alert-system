import React, { useState, useEffect } from 'react';
import {
  Building2,
  TrendingUp,
  Search,
  DollarSign,
  PieChart,
  ShieldCheck,
  Percent,
  Activity,
  AlertCircle,
  ExternalLink,
  Layers,
  FileText,
} from 'lucide-react';
import { researchApi } from '../services/api';
import { CompanyFundamentals } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

const POPULAR_TICKERS = [
  'RELIANCE.NS',
  'TCS.NS',
  'INFY.NS',
  'HDFCBANK.NS',
  'ICICIBANK.NS',
  'SBIN.NS',
  'TATAMOTORS.NS',
  'ITC.NS',
  'BHARTIARTL.NS',
];

export const FundamentalsPage: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE.NS');
  const [inputSymbol, setInputSymbol] = useState<string>('RELIANCE.NS');
  const [data, setData] = useState<CompanyFundamentals | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFundamentals = async (sym: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await researchApi.getFundamentals(sym);
      setData(res);
      setSelectedSymbol(sym);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch fundamentals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFundamentals(selectedSymbol);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputSymbol.trim()) {
      fetchFundamentals(inputSymbol.trim());
    }
  };

  const formatNumber = (val: number | null | undefined, suffix = '', decimals = 2) => {
    if (val === null || val === undefined) return <span className="text-slate-400 italic">UNAVAILABLE</span>;
    return `${val.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;
  };

  const formatCurrencyInLakhCr = (val: number | null | undefined) => {
    if (val === null || val === undefined) return <span className="text-slate-400 italic">UNAVAILABLE</span>;
    // 1 Lakh Cr = 10^12
    const inLakhCr = val / 1e12;
    if (inLakhCr >= 1.0) {
      return `₹${inLakhCr.toFixed(2)} Lakh Cr`;
    }
    // 1 Cr = 10^7
    const inCr = val / 1e7;
    return `₹${inCr.toFixed(2)} Cr`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Building2 className="w-7 h-7 text-cyan-400" />
            Company Fundamentals & Valuation
          </h1>
          <p className="text-sm text-slate-400">
            Audited financial statements, valuation multiples, profitability margins, and financial solvency
          </p>
        </div>

        {/* Search & Quick Select */}
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputSymbol}
              onChange={(e) => setInputSymbol(e.target.value.toUpperCase())}
              placeholder="Enter symbol (e.g. TCS.NS)"
              className="pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 w-56"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition"
          >
            Search
          </button>
        </form>
      </div>

      {/* Quick Ticker Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 font-medium shrink-0">Popular:</span>
        {POPULAR_TICKERS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setInputSymbol(t);
              fetchFundamentals(t);
            }}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition ${
              selectedSymbol === t
                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-slate-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <LoadingSpinner size="lg" />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Company Profile Header Card */}
          <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-slate-100">{data.company_name}</h2>
                  <span className="px-2.5 py-0.5 text-xs font-semibold rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                    {data.symbol}
                  </span>
                  <Badge variant={data.data_freshness === 'FRESH' ? 'success' : 'warning'}>
                    {data.data_freshness} DATA
                  </Badge>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  Sector: <span className="text-slate-200 font-medium">{data.sector}</span> | Industry:{' '}
                  <span className="text-slate-200 font-medium">{data.industry}</span>
                </p>
              </div>

              <div className="text-right text-xs text-slate-400 space-y-1">
                <div>
                  Source: <span className="text-slate-300 font-medium">{data.data_source}</span>
                </div>
                <div>
                  Reporting Period: <span className="text-cyan-400 font-semibold">{data.reporting_period}</span>
                </div>
                {data.website && (
                  <a
                    href={data.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
                  >
                    <span>Official Website</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>

            {/* Business Summary */}
            {data.business_summary && (
              <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-lg border border-slate-800/80">
                {data.business_summary}
              </p>
            )}
          </div>

          {/* 4 Category Metric Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* 1. Valuation Multiples */}
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center space-x-2 text-cyan-400 border-b border-slate-800 pb-3">
                <PieChart className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">Valuation Multiples</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Market Cap</span>
                  <span className="font-semibold text-slate-100">{formatCurrencyInLakhCr(data.valuation.market_cap)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Trailing P/E</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.valuation.trailing_pe, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Forward P/E</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.valuation.forward_pe, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Price to Book (P/B)</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.valuation.price_to_book, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Price to Sales (P/S)</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.valuation.price_to_sales, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">EV / EBITDA</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.valuation.ev_to_ebitda, 'x')}</span>
                </div>
              </div>
            </div>

            {/* 2. Topline & Growth */}
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center space-x-2 text-emerald-400 border-b border-slate-800 pb-3">
                <TrendingUp className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">Financial Growth (TTM)</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Total Revenue</span>
                  <span className="font-semibold text-slate-100">{formatCurrencyInLakhCr(data.financial_performance?.total_revenue)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Revenue Growth (YoY)</span>
                  <span className={`font-semibold ${(data.growth?.revenue_growth_yoy_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {formatNumber(data.growth?.revenue_growth_yoy_pct, '%')}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Net Profit</span>
                  <span className="font-semibold text-slate-100">{formatCurrencyInLakhCr(data.financial_performance?.net_profit)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Profit Growth (YoY)</span>
                  <span className={`font-semibold ${(data.growth?.profit_growth_yoy_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {formatNumber(data.growth?.profit_growth_yoy_pct, '%')}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Trailing EPS</span>
                  <span className="font-semibold text-slate-100">₹{formatNumber(data.financial_performance?.trailing_eps)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Forward EPS</span>
                  <span className="font-semibold text-slate-100">₹{formatNumber(data.financial_performance?.forward_eps)}</span>
                </div>
              </div>
            </div>

            {/* 3. Profitability & Returns */}
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center space-x-2 text-blue-400 border-b border-slate-800 pb-3">
                <Percent className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">Profitability & Returns</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Return on Equity (ROE)</span>
                  <span className="font-semibold text-cyan-400">{formatNumber(data.profitability?.roe_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">ROCE (Capital Employed)</span>
                  <span className="font-semibold text-cyan-400">{formatNumber(data.profitability?.roce_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Return on Assets (ROA)</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.profitability?.roa_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Operating Margin</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.profitability?.operating_margin_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Net Profit Margin</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.profitability?.net_margin_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Free Cash Flow</span>
                  <span className="font-semibold text-slate-100">{formatCurrencyInLakhCr(data.profitability?.free_cash_flow)}</span>
                </div>
              </div>
            </div>

            {/* 4. Balance Sheet Health */}
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center space-x-2 text-amber-400 border-b border-slate-800 pb-3">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-semibold text-slate-100">Health & Dividends</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Debt to Equity</span>
                  <span className={`font-semibold ${(data.financial_health?.debt_to_equity ?? 0) > 1.5 ? 'text-rose-400' : 'text-slate-100'}`}>
                    {formatNumber(data.financial_health?.debt_to_equity, 'x')}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Current Ratio</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.financial_health?.current_ratio, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Quick Ratio</span>
                  <span className="font-semibold text-slate-100">{formatNumber(data.financial_health?.quick_ratio, 'x')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Dividend Yield</span>
                  <span className="font-semibold text-emerald-400">{formatNumber(data.financial_health?.dividend_yield_pct, '%')}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Currency</span>
                  <span className="font-semibold text-slate-300">{data.currency}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Missing Metrics & Transparency Section */}
          {data.missing_metrics && data.missing_metrics.length > 0 && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <span className="font-semibold text-slate-200">Regulatory Disclosure Transparency Notice:</span>
                <p className="text-slate-400">
                  The following financial ratios were not disclosed in company filings or standard regulatory feeds and are displayed as UNAVAILABLE rather than estimated: {data.missing_metrics.join(', ')}.
                </p>
              </div>
            </div>
          )}

          {/* Mandatory Regulatory Disclaimer */}
          <div className="text-xs text-slate-400 text-center border-t border-slate-800/80 pt-4">
            {data.disclaimer}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default FundamentalsPage;

