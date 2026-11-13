import React, { useState, useEffect } from 'react';
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Search,
  ExternalLink,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Layers,
  Activity,
  ChevronDown,
  ChevronUp,
  BarChart2,
  PieChart,
  CheckCircle2,
  Tag,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { newsApi } from '../services/api';
import {
  NewsItem,
  CompanySentimentSummary,
  SentimentTimelinePoint,
  MarketNewsOverview,
  NewsCorrelation,
  NewsAlertItem,
} from '../types';
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

const CATEGORIES = [
  'ALL',
  'EARNINGS',
  'REGULATORY',
  'CORPORATE_ACTION',
  'BUSINESS_EXPANSION',
  'MACRO',
  'MARKET',
];

const SENTIMENT_FILTERS = ['ALL', 'POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED'];

export const NewsIntelligencePage: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE.NS');
  const [symbolInput, setSymbolInput] = useState<string>('RELIANCE.NS');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [sentimentFilter, setSentimentFilter] = useState<string>('ALL');
  const [timeframe, setTimeframe] = useState<string>('7d');

  // State
  const [marketOverview, setMarketOverview] = useState<MarketNewsOverview | null>(null);
  const [companySentiment, setCompanySentiment] = useState<CompanySentimentSummary | null>(null);
  const [sentimentTimeline, setSentimentTimeline] = useState<SentimentTimelinePoint[]>([]);
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [newsAlerts, setNewsAlerts] = useState<NewsAlertItem[]>([]);

  // Correlation drawer per article
  const [expandedCorrelation, setExpandedCorrelation] = useState<Record<number, NewsCorrelation | null>>({});
  const [loadingCorrelation, setLoadingCorrelation] = useState<Record<number, boolean>>({});

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (sym: string, tf: string) => {
    try {
      setLoading(true);
      setError(null);

      const [overviewRes, compSentRes, timelineRes, newsRes, alertsRes] = await Promise.all([
        newsApi.getMarketOverview(),
        newsApi.getCompanySentiment(sym, tf),
        newsApi.getSentimentTrends(sym, 14),
        newsApi.getNews({
          symbol: sym,
          category: categoryFilter !== 'ALL' ? categoryFilter : undefined,
          sentiment_label: sentimentFilter !== 'ALL' ? sentimentFilter : undefined,
          limit: 25,
        }),
        newsApi.getNewsAlerts(10),
      ]);

      setMarketOverview(overviewRes);
      setCompanySentiment(compSentRes);
      setSentimentTimeline(timelineRes);
      setNewsItems(newsRes.items);
      setNewsAlerts(alertsRes);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load news intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedSymbol, timeframe);
  }, [selectedSymbol, timeframe, categoryFilter, sentimentFilter]);

  const handleRefreshFeed = async () => {
    try {
      setRefreshing(true);
      await newsApi.refreshNews([selectedSymbol, 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS']);
      await fetchData(selectedSymbol, timeframe);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to refresh news feed.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleSelectSymbol = (sym: string) => {
    setSelectedSymbol(sym);
    setSymbolInput(sym);
  };

  const handleToggleCorrelation = async (newsId: number) => {
    if (expandedCorrelation[newsId]) {
      setExpandedCorrelation((prev) => ({ ...prev, [newsId]: null }));
      return;
    }

    try {
      setLoadingCorrelation((prev) => ({ ...prev, [newsId]: true }));
      const cor = await newsApi.getNewsCorrelation(newsId);
      setExpandedCorrelation((prev) => ({ ...prev, [newsId]: cor }));
    } catch (err: any) {
      setError('Could not calculate news-to-price correlation for this item.');
    } finally {
      setLoadingCorrelation((prev) => ({ ...prev, [newsId]: false }));
    }
  };

  const getSentimentBadge = (label?: string, score?: number) => {
    switch (label) {
      case 'POSITIVE':
        return (
          <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            POSITIVE ({score != null ? `${score > 0 ? '+' : ''}${score.toFixed(2)}` : ''})
          </span>
        );
      case 'NEGATIVE':
        return (
          <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800 flex items-center gap-1">
            <TrendingDown className="w-3 h-3" />
            NEGATIVE ({score != null ? score.toFixed(2) : ''})
          </span>
        );
      case 'MIXED':
        return (
          <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-950 text-amber-400 border border-amber-800 flex items-center gap-1">
            <Activity className="w-3 h-3" />
            MIXED ({score != null ? `${score > 0 ? '+' : ''}${score.toFixed(2)}` : ''})
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            NEUTRAL (0.00)
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Newspaper className="w-7 h-7 text-cyan-400" />
            Financial News Intelligence & Sentiment Analysis
          </h1>
          <p className="text-sm text-slate-400">
            Real-time corporate announcements, entity sentiment tracking, and news-to-price correlation
          </p>
        </div>

        <button
          onClick={handleRefreshFeed}
          disabled={refreshing}
          className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-40 text-white font-medium rounded-lg text-sm flex items-center gap-2 transition shadow-md self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Scanning Wire...' : 'Refresh News Wire'}</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* A. Market Sentiment Overview Banner */}
      {marketOverview && (
        <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2 text-cyan-400">
              <PieChart className="w-5 h-5" />
              <h2 className="font-semibold text-slate-100">Market-Wide Sentiment Overview (7 Days)</h2>
            </div>
            <span className="text-xs text-slate-400">
              Total Articles Analyzed: <strong className="text-slate-200">{marketOverview.total_articles}</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
            <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-800 text-center space-y-1">
              <span className="text-xs text-slate-400">Market Sentiment Score</span>
              <div className="text-2xl font-bold text-cyan-400">
                {marketOverview.average_score > 0 ? '+' : ''}{marketOverview.average_score.toFixed(2)}
              </div>
              <div className="text-xs font-semibold text-slate-300">
                Overall: {marketOverview.overall_sentiment}
              </div>
            </div>

            <div className="md:col-span-3 space-y-2">
              <div className="flex justify-between text-xs text-slate-400 font-medium">
                <span className="text-emerald-400">Positive: {marketOverview.distribution.positive}</span>
                <span className="text-rose-400">Negative: {marketOverview.distribution.negative}</span>
                <span className="text-slate-300">Neutral: {marketOverview.distribution.neutral}</span>
                <span className="text-amber-400">Mixed: {marketOverview.distribution.mixed}</span>
              </div>

              {/* Multi-segment progress bar */}
              <div className="h-3 w-full bg-slate-900 rounded-full overflow-hidden flex border border-slate-800">
                {marketOverview.total_articles > 0 ? (
                  <>
                    <div
                      style={{ width: `${(marketOverview.distribution.positive / marketOverview.total_articles) * 100}%` }}
                      className="bg-emerald-500 h-full"
                    />
                    <div
                      style={{ width: `${(marketOverview.distribution.negative / marketOverview.total_articles) * 100}%` }}
                      className="bg-rose-500 h-full"
                    />
                    <div
                      style={{ width: `${(marketOverview.distribution.neutral / marketOverview.total_articles) * 100}%` }}
                      className="bg-slate-500 h-full"
                    />
                    <div
                      style={{ width: `${(marketOverview.distribution.mixed / marketOverview.total_articles) * 100}%` }}
                      className="bg-amber-500 h-full"
                    />
                  </>
                ) : (
                  <div className="w-full bg-slate-800 h-full" />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* B. Company Sentiment Tracker */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2 text-cyan-400">
            <Activity className="w-5 h-5" />
            <h2 className="font-semibold text-slate-100">Stock Sentiment Trend Analyzer</h2>
          </div>

          {/* Timeframe Controls */}
          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
            {['1d', '7d', '30d'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition uppercase ${
                  timeframe === tf
                    ? 'bg-cyan-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Popular Tickers Chips */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 font-medium shrink-0">Tracked Stock:</span>
          {POPULAR_TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => handleSelectSymbol(t)}
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

        {companySentiment && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Company Sentiment Posture</span>
                <span className="text-xs font-bold text-cyan-400">{companySentiment.symbol}</span>
              </div>
              <div className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                <span>{companySentiment.average_sentiment_score > 0 ? '+' : ''}{companySentiment.average_sentiment_score.toFixed(2)}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {companySentiment.sentiment_trend}
                </span>
              </div>
              {companySentiment.is_insufficient_data && (
                <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-950/40 p-2 rounded border border-amber-900/60">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>{companySentiment.message}</span>
                </div>
              )}
            </div>

            {/* Daily Timeline Chart */}
            <div className="md:col-span-2 bg-slate-900/80 p-4 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-400 block mb-2 font-medium">14-Day Sentiment Trajectory</span>
              <div className="h-28 w-full">
                {sentimentTimeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={sentimentTimeline}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis
                        dataKey="date"
                        stroke="#64748B"
                        tick={{ fill: '#64748B', fontSize: 10 }}
                        tickFormatter={(val) => val.slice(5)}
                      />
                      <YAxis
                        stroke="#64748B"
                        domain={[-1, 1]}
                        tick={{ fill: '#64748B', fontSize: 10 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0F172A',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          fontSize: '11px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="avg_sentiment_score"
                        stroke="#38BDF8"
                        fill="#38BDF820"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-xs text-slate-500">
                    No timeline history recorded for this period.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* C. Intelligent News Alerts Bar (if any alerts) */}
      {newsAlerts.length > 0 && (
        <div className="bg-[#131B2E] border border-rose-900/50 rounded-xl p-4 shadow-lg space-y-3">
          <div className="flex items-center space-x-2 text-rose-400">
            <ShieldAlert className="w-5 h-5" />
            <h3 className="font-semibold text-slate-100">Intelligent News Notifications ({newsAlerts.length})</h3>
          </div>
          <div className="space-y-2">
            {newsAlerts.slice(0, 3).map((alert) => (
              <div
                key={alert.id}
                className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg text-xs flex items-start justify-between gap-3"
              >
                <div>
                  <div className="font-semibold text-slate-200">{alert.title}</div>
                  <p className="text-slate-400 mt-0.5">{alert.message}</p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                    alert.severity === 'CRITICAL'
                      ? 'bg-rose-950 text-rose-400 border border-rose-800'
                      : alert.severity === 'HIGH'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-blue-950 text-blue-400 border border-blue-800'
                  }`}
                >
                  {alert.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* D. Market News Feed with Category & Sentiment Filters */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2 text-cyan-400">
            <Layers className="w-5 h-5" />
            <h2 className="font-semibold text-slate-100">Financial News Wire & AI Signals</h2>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Category:</span>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                  categoryFilter === cat
                    ? 'bg-cyan-500 text-slate-950 shadow'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Sentiment Filter Row */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium shrink-0">Sentiment Filter:</span>
          {SENTIMENT_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setSentimentFilter(s)}
              className={`px-2.5 py-1 rounded font-semibold transition ${
                sentimentFilter === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* News Feed Cards */}
        {loading ? (
          <div className="py-20 flex justify-center">
            <LoadingSpinner size="lg" />
          </div>
        ) : newsItems.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-sm">
            No verified news articles found matching the selected filters.
          </div>
        ) : (
          <div className="space-y-4">
            {newsItems.map((item) => (
              <div
                key={item.id}
                className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700 transition shadow-md space-y-3"
              >
                {/* Meta Row: Source, Time, Timing, Sentiment */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-400">
                    <span className="font-semibold text-slate-300">{item.source}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {item.published_at ? new Date(item.published_at).toLocaleString() : ''}
                    </span>
                    {item.market_session_timing && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
                        {item.market_session_timing}
                      </span>
                    )}
                    <span className="px-1.5 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-900 text-[10px]">
                      {item.category}
                    </span>
                  </div>

                  <div>{getSentimentBadge(item.sentiment?.sentiment_label, item.sentiment?.sentiment_score)}</div>
                </div>

                {/* Title & Link */}
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-base font-semibold text-slate-100 hover:text-cyan-400 transition leading-snug">
                    <a href={item.url} target="_blank" rel="noreferrer">
                      {item.title}
                    </a>
                  </h3>
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-400 hover:text-cyan-400 shrink-0 p-1"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>

                {/* AI Summary / Snippet */}
                {item.sentiment?.ai_summary && (
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-lg border border-slate-800/60">
                    {item.sentiment.ai_summary}
                  </p>
                )}

                {/* Financial Figures & Mentioned Entities */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {item.sentiment?.companies_mentioned?.map((c, cIdx) => (
                    <span key={cIdx} className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[11px] font-semibold">
                      {c}
                    </span>
                  ))}
                  {item.sentiment?.financial_figures?.map((f, fIdx) => (
                    <span key={fIdx} className="px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700 text-[11px] font-mono">
                      {f}
                    </span>
                  ))}
                </div>

                {/* Correlation Toggle Button */}
                {item.symbol && (
                  <div className="pt-2 border-t border-slate-800/80">
                    <button
                      onClick={() => handleToggleCorrelation(item.id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1.5 transition"
                    >
                      <BarChart2 className="w-3.5 h-3.5" />
                      <span>
                        {expandedCorrelation[item.id] ? 'Hide Price Correlation' : 'View Stock Price Correlation'}
                      </span>
                      {expandedCorrelation[item.id] ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>

                    {/* Correlation Drawer */}
                    {loadingCorrelation[item.id] && (
                      <div className="pt-2 flex items-center gap-2 text-xs text-cyan-400">
                        <LoadingSpinner size="sm" />
                        <span>Calculating historical price reaction...</span>
                      </div>
                    )}

                    {expandedCorrelation[item.id] && (
                      <div className="mt-3 p-4 bg-slate-950/80 rounded-lg border border-slate-800 space-y-3 text-xs">
                        <div className="flex items-center justify-between font-semibold text-slate-200">
                          <span>Trading Session Reaction: {expandedCorrelation[item.id]?.trading_session_date}</span>
                          <span className="text-slate-400">Timing: {expandedCorrelation[item.id]?.market_session_timing}</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-slate-300">
                          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                            <span className="text-slate-400 block mb-0.5">Price Before</span>
                            <span className="font-bold text-slate-100">
                              ₹{expandedCorrelation[item.id]?.price_metrics.price_before_publication?.toFixed(2)}
                            </span>
                          </div>
                          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                            <span className="text-slate-400 block mb-0.5">Session Close</span>
                            <span className="font-bold text-slate-100">
                              ₹{expandedCorrelation[item.id]?.price_metrics.session_close_price?.toFixed(2)}
                            </span>
                          </div>
                          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                            <span className="text-slate-400 block mb-0.5">Session Move</span>
                            <span
                              className={`font-bold ${
                                (expandedCorrelation[item.id]?.price_metrics.session_change_pct ?? 0) >= 0
                                  ? 'text-emerald-400'
                                  : 'text-rose-400'
                              }`}
                            >
                              {(expandedCorrelation[item.id]?.price_metrics.session_change_pct ?? 0) >= 0 ? '+' : ''}
                              {expandedCorrelation[item.id]?.price_metrics.session_change_pct}%
                            </span>
                          </div>
                          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                            <span className="text-slate-400 block mb-0.5">Volume Ratio</span>
                            <span className="font-bold text-cyan-400">
                              {expandedCorrelation[item.id]?.volume_metrics.volume_ratio}x
                            </span>
                          </div>
                        </div>

                        {expandedCorrelation[item.id]?.detected_market_events?.length ? (
                          <div className="text-amber-400 bg-amber-950/30 p-2 rounded border border-amber-900/50">
                            Detected Market Events:{' '}
                            {expandedCorrelation[item.id]?.detected_market_events
                              ?.map((e) => `${e.event_type} (${e.severity})`)
                              .join(', ')}
                          </div>
                        ) : null}

                        <p className="text-[11px] text-slate-400 italic">
                          {expandedCorrelation[item.id]?.correlation_disclaimer}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsIntelligencePage;
