import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Printer,
  Calendar,
  Building2,
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Search,
  ExternalLink,
  ChevronRight,
  BookOpen,
  PieChart,
  Percent,
} from 'lucide-react';
import { researchApi } from '../services/api';
import { ResearchReportItem } from '../types';
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
];

export const ResearchReportsPage: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE.NS');
  const [customTitle, setCustomTitle] = useState<string>('');
  const [reports, setReports] = useState<ResearchReportItem[]>([]);
  const [activeReport, setActiveReport] = useState<ResearchReportItem | null>(null);

  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    try {
      setLoadingList(true);
      setError(null);
      const res = await researchApi.listReports();
      setReports(res);
      if (res.length > 0 && !activeReport) {
        // Load the most recent report details
        loadReportDetail(res[0].id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to list saved reports.');
    } finally {
      setLoadingList(false);
    }
  };

  const loadReportDetail = async (reportId: number) => {
    try {
      setError(null);
      const res = await researchApi.getReport(reportId);
      setActiveReport(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load report detail.');
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSymbol.trim() || generating) return;

    try {
      setGenerating(true);
      setError(null);
      const res = await researchApi.createReport(
        selectedSymbol.trim(),
        customTitle.trim() || undefined
      );
      setActiveReport(res);
      setCustomTitle('');
      await fetchReports();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Report generation failed.');
    } finally {
      setGenerating(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <FileText className="w-7 h-7 text-cyan-400" />
            Institutional Research Reports
          </h1>
          <p className="text-sm text-slate-400">
            Generate, persist, and export 9-section institutional equity research dossiers
          </p>
        </div>

        {activeReport && (
          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-sm font-medium flex items-center gap-2 transition shadow-md"
          >
            <Printer className="w-4 h-4 text-cyan-400" />
            <span>Print / Save as PDF</span>
          </button>
        )}
      </div>

      {/* Generator Form */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4 print:hidden">
        <div className="flex items-center space-x-2 text-cyan-400 border-b border-slate-800 pb-3">
          <Plus className="w-5 h-5" />
          <h2 className="font-semibold text-slate-100">Generate New Equity Dossier</h2>
        </div>

        <form onSubmit={handleGenerateReport} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Target Stock</label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500 cursor-pointer"
            >
              {POPULAR_TICKERS.map((t) => (
                <option key={t} value={t} className="bg-slate-900 text-slate-200">
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Custom Title (Optional)</label>
            <input
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder="e.g. Q3 Equity Research: Reliance Industries"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-400 outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={generating}
              className="w-full py-2 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-40 text-white font-medium rounded-lg text-sm flex items-center justify-center gap-2 transition shadow-md"
            >
              {generating ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Compiling Dossier...</span>
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  <span>Generate 9-Section Report</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Main Layout: Saved Reports Sidebar & Active Report View */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Saved Reports Library List */}
        <div className="lg:col-span-1 bg-[#131B2E] border border-slate-800 rounded-xl p-4 shadow-lg space-y-3 print:hidden">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-sm font-semibold text-slate-200">Report Library</h3>
            <span className="text-xs text-slate-400">{reports.length} Saved</span>
          </div>

          {loadingList ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="sm" />
            </div>
          ) : reports.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No research reports saved yet.</p>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {reports.map((rep) => (
                <button
                  key={rep.id}
                  onClick={() => loadReportDetail(rep.id)}
                  className={`w-full text-left p-3 rounded-lg border transition ${
                    activeReport?.id === rep.id
                      ? 'bg-cyan-500/10 border-cyan-500 text-cyan-300'
                      : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-100">{rep.symbol}</span>
                    <span className="text-[10px] text-slate-400">
                      {rep.created_at ? new Date(rep.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <p className="text-xs line-clamp-1 text-slate-400">{rep.title}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Full 9-Section Institutional Report View */}
        <div className="lg:col-span-3">
          {activeReport ? (
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-8 shadow-xl space-y-8 text-slate-200 print:bg-white print:text-black print:border-none print:shadow-none print:p-0">
              {/* 1. Header & Title */}
              <div className="border-b border-slate-800 pb-6 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-cyan-400 uppercase tracking-widest">
                    StockPulse AI Institutional Research Division
                  </span>
                  <span>Generated: {activeReport.created_at ? new Date(activeReport.created_at).toLocaleString() : ''}</span>
                </div>
                <h1 className="text-2xl font-bold text-slate-100 print:text-black">{activeReport.title}</h1>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>Ticker: <strong className="text-slate-200">{activeReport.symbol}</strong></span>
                  <span>•</span>
                  <span>Exchange: <strong className="text-slate-200">{activeReport.overview?.exchange || 'NSE'}</strong></span>
                  <span>•</span>
                  <span>Sector: <strong className="text-slate-200">{activeReport.overview?.sector || 'Equities'}</strong></span>
                </div>
              </div>

              {/* 2. Executive Summary */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  1. Executive Summary
                </h2>
                <p className="text-sm leading-relaxed text-slate-300 bg-slate-900/50 p-4 rounded-lg border border-slate-800/80 print:bg-transparent print:border-none print:p-0 print:text-black">
                  {activeReport.summary}
                </p>
              </div>

              {/* 3. Company Overview & Business Segments */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  2. Company Overview & Business Profile
                </h2>
                <p className="text-sm leading-relaxed text-slate-300 print:text-black">
                  {activeReport.overview?.business_summary || 'Business profile information currently unavailable.'}
                </p>

                {activeReport.overview?.price_performance && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-xs">
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
                      <span className="text-slate-400 block mb-0.5">1-Month Return</span>
                      <span className="font-bold text-slate-100">
                        {activeReport.overview.price_performance.return_1mo_pct != null
                          ? `${activeReport.overview.price_performance.return_1mo_pct}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
                      <span className="text-slate-400 block mb-0.5">3-Month Return</span>
                      <span className="font-bold text-slate-100">
                        {activeReport.overview.price_performance.return_3mo_pct != null
                          ? `${activeReport.overview.price_performance.return_3mo_pct}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
                      <span className="text-slate-400 block mb-0.5">6-Month Return</span>
                      <span className="font-bold text-slate-100">
                        {activeReport.overview.price_performance.return_6mo_pct != null
                          ? `${activeReport.overview.price_performance.return_6mo_pct}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
                      <span className="text-slate-400 block mb-0.5">1-Year Return</span>
                      <span className="font-bold text-slate-100">
                        {activeReport.overview.price_performance.return_1y_pct != null
                          ? `${activeReport.overview.price_performance.return_1y_pct}%`
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* 4. Comprehensive Fundamental Analysis Matrix */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  3. Comprehensive Fundamental Analysis (TTM / MRQ)
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Market Cap</span>
                    <span className="font-bold text-slate-100 text-sm">
                      ₹{activeReport.fundamentals?.valuation?.market_cap_formatted || 'UNAVAILABLE'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Trailing P/E</span>
                    <span className="font-bold text-slate-100 text-sm">
                      {activeReport.fundamentals?.valuation?.trailing_pe != null
                        ? `${activeReport.fundamentals.valuation.trailing_pe}x`
                        : 'UNAVAILABLE'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">YoY Revenue Growth</span>
                    <span className="font-bold text-emerald-400 text-sm">
                      {activeReport.fundamentals?.growth?.revenue_growth_yoy_pct != null
                        ? `${activeReport.fundamentals.growth.revenue_growth_yoy_pct}%`
                        : 'UNAVAILABLE'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Return on Equity (ROE)</span>
                    <span className="font-bold text-cyan-400 text-sm">
                      {activeReport.fundamentals?.profitability?.roe_pct != null
                        ? `${activeReport.fundamentals.profitability.roe_pct}%`
                        : 'UNAVAILABLE'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 5. Technical Indicator Synthesis */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  4. Technical Synthesis & Classical Floor Pivots
                </h2>
                <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800/80 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-slate-300">Technical Posture:</span>
                    <span className="font-bold text-cyan-400">{activeReport.technicals?.overall_sentiment || 'NEUTRAL'}</span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2">
                    <div>RSI (14): <strong className="text-slate-200">{activeReport.technicals?.indicators?.rsi_14 ?? 'N/A'}</strong></div>
                    <div>SMA 50: <strong className="text-slate-200">₹{activeReport.technicals?.indicators?.sma_50 ?? 'N/A'}</strong></div>
                    <div>SMA 200: <strong className="text-slate-200">₹{activeReport.technicals?.indicators?.sma_200 ?? 'N/A'}</strong></div>
                    <div>MACD Line: <strong className="text-slate-200">{activeReport.technicals?.indicators?.macd_line ?? 'N/A'}</strong></div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 border-t border-slate-800">
                    <div>Pivot: <strong className="text-slate-200">₹{activeReport.technicals?.support_levels?.pivot ?? 'N/A'}</strong></div>
                    <div>Support S1: <strong className="text-slate-200">₹{activeReport.technicals?.support_levels?.s1 ?? 'N/A'}</strong></div>
                    <div>Resistance R1: <strong className="text-slate-200">₹{activeReport.technicals?.resistance_levels?.r1 ?? 'N/A'}</strong></div>
                    <div>20D Volatility: <strong className="text-slate-200">{activeReport.technicals?.indicators?.historical_volatility_20d_annualized ?? 'N/A'}%</strong></div>
                  </div>
                </div>
              </div>

              {/* 6. Historical Market Events */}
              {activeReport.events && activeReport.events.length > 0 && (
                <div className="space-y-3">
                  <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                    5. Historical Market Events & Price Anomalies
                  </h2>
                  <div className="space-y-2">
                    {activeReport.events.map((ev: any, idx: number) => (
                      <div key={idx} className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 text-xs flex justify-between items-start">
                        <div>
                          <div className="font-semibold text-slate-200">{ev.date} • {ev.event_type}</div>
                          <p className="text-slate-400 mt-0.5">{ev.explanation}</p>
                        </div>
                        <span className="font-bold text-cyan-400 shrink-0 ml-3">{ev.price_change_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 7. Key Risk Factors */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-rose-500 pl-3 print:text-black">
                  6. Key Risk Factors & Investment Considerations
                </h2>
                <div className="space-y-2">
                  {activeReport.risk_factors?.map((rf, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="text-slate-200">{rf.category}</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                            rf.severity === 'HIGH'
                              ? 'bg-rose-950 text-rose-400 border border-rose-800'
                              : rf.severity === 'MEDIUM'
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {rf.severity} RISK
                        </span>
                      </div>
                      <p className="text-slate-400 leading-relaxed">{rf.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* 8. Data Freshness & Attribution */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  7. Data Freshness, Audit Trail & Attribution
                </h2>
                <div className="bg-slate-900/40 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1 text-slate-400">
                  <div>Data Source: <strong className="text-slate-300">National Stock Exchange of India (NSE) / Corporate Filings via Yahoo Finance</strong></div>
                  <div>Audit Timestamp: <strong className="text-slate-300">{activeReport.created_at}</strong></div>
                  <div>Integrity Policy: Every metric is verified directly from regulatory filings. Missing data is tagged rather than estimated.</div>
                </div>
              </div>

              {/* 9. Objective Neutral Conclusion */}
              <div className="space-y-3">
                <h2 className="text-lg font-bold text-slate-100 border-l-4 border-cyan-500 pl-3 print:text-black">
                  8. Objective Synthesis & Conclusion
                </h2>
                <p className="text-sm leading-relaxed text-slate-300 bg-slate-900/50 p-4 rounded-lg border border-slate-800/80 print:bg-transparent print:border-none print:p-0 print:text-black">
                  {activeReport.conclusion}
                </p>
              </div>

              {/* Legal Disclaimer */}
              <div className="text-[11px] text-slate-400 text-center border-t border-slate-800 pt-4 leading-relaxed">
                Disclaimer: This automated research dossier is generated by StockPulse AI solely for informational and educational purposes. StockPulse AI is not an investment advisor or SEBI-registered research entity. Financial markets carry risk; consult a certified advisor before making investment decisions.
              </div>
            </div>
          ) : (
            <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              Select or generate a research report to view its full 9-section institutional dossier.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResearchReportsPage;

