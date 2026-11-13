import React, { useState, useEffect, useRef } from 'react';
import {
  Brain,
  Send,
  Sparkles,
  ShieldCheck,
  Lock,
  ExternalLink,
  BookOpen,
  Info,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { researchApi } from '../services/api';
import { ResearchChatMessageItem } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
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

const PRESET_PROMPTS = [
  'Analyse RELIANCE.NS fundamentals, valuation and growth',
  'Why did this stock move sharply in recent sessions?',
  'Explain whether the technical indicators show bullish or bearish momentum',
  'What are the key financial risks and balance sheet concerns?',
  'Compare RELIANCE.NS and TCS.NS across valuation and margins',
];

export const ResearchAssistantPage: React.FC = () => {
  const [sessionId] = useState<string>(() => `session-${Date.now()}`);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE.NS');
  const [includePortfolio, setIncludePortfolio] = useState<boolean>(false);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [messages, setMessages] = useState<ResearchChatMessageItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initial welcome message
  useEffect(() => {
    setMessages([
      {
        session_id: sessionId,
        symbol: 'RELIANCE.NS',
        role: 'assistant',
        content: `### Welcome to StockPulse AI Research Assistant
I am your institutional-grade research companion for Indian equities (NSE/BSE).

**What I do:**
- **Fundamentals**: Deep analysis of audited financials, P/E multiples, revenue/profit growth, and ROE/ROCE.
- **Technicals**: Real-time Wilder RSI 14, MACD crossovers, moving average stacked alignment, and classic floor pivot points.
- **Market Events**: Evidence-grounded explanations for price and volume anomalies.
- **Risk Intelligence**: Objective evaluation of financial leverage, valuation risk, and technical divergence.

Select a stock or choose a prompt below to begin your analysis.`,
        sources: [
          {
            source: 'StockPulse AI Synthesis Engine',
            category: 'System Initialization',
            timestamp: new Date().toISOString(),
            details: 'Initialized with strict zero-hallucination guardrails and source attribution.',
          },
        ],
        provider_used: 'StockPulse AI Core',
        created_at: new Date().toISOString(),
      },
    ]);
  }, [sessionId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const msg = textToSend || inputMessage;
    if (!msg.trim() || loading) return;

    const userMsg: ResearchChatMessageItem = {
      session_id: sessionId,
      symbol: selectedSymbol,
      role: 'user',
      content: msg.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const resp = await researchApi.chat(
        msg.trim(),
        sessionId,
        selectedSymbol || undefined,
        includePortfolio
      );
      setMessages((prev) => [...prev, resp]);
    } catch (err: any) {
      const errorMsg: ResearchChatMessageItem = {
        session_id: sessionId,
        role: 'assistant',
        content: `⚠️ **Unable to complete research query**: ${err?.response?.data?.detail || err?.message || 'Server error'}. Please verify market connection and try again.`,
        created_at: new Date().toISOString(),
        provider_used: 'Error Handler',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (idx: number) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] max-w-7xl mx-auto space-y-4">
      {/* Top Header & Context Bar */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-cyan-400">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              AI Stock Research Assistant
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-900/40 text-cyan-300 border border-cyan-700/50">
                Institutional Grade
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              CFA-level financial analysis grounded in verified NSE/BSE filings, indicators, and market events
            </p>
          </div>
        </div>

        {/* Controls: Stock Selector & Privacy Toggle */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-700/60 rounded-lg px-3 py-1.5">
            <span className="text-xs text-slate-400 font-medium">Focus Ticker:</span>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-transparent text-sm font-semibold text-cyan-400 outline-none cursor-pointer"
            >
              {POPULAR_TICKERS.map((t) => (
                <option key={t} value={t} className="bg-slate-900 text-slate-200">
                  {t}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center space-x-2 bg-slate-900/80 border border-slate-700/60 rounded-lg px-3 py-1.5 cursor-pointer hover:border-slate-600 transition">
            <input
              type="checkbox"
              checked={includePortfolio}
              onChange={(e) => setIncludePortfolio(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
            />
            <span className="text-xs text-slate-300 font-medium flex items-center gap-1.5">
              {includePortfolio ? (
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Lock className="w-3.5 h-3.5 text-slate-400" />
              )}
              Authorize Portfolio Holdings
            </span>
          </label>
        </div>
      </div>

      {/* Main Conversation Window */}
      <div className="flex-1 bg-[#131B2E] border border-slate-800 rounded-xl p-5 overflow-y-auto space-y-5 shadow-inner">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${
              m.role === 'user' ? 'items-end' : 'items-start'
            } space-y-1.5`}
          >
            <div className="flex items-center space-x-2 text-xs text-slate-400 px-1">
              <span className="font-semibold text-slate-300">
                {m.role === 'user' ? 'You' : 'StockPulse AI Analyst'}
              </span>
              <span>•</span>
              <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              {m.provider_used && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                  {m.provider_used}
                </span>
              )}
            </div>

            <div
              className={`max-w-3xl rounded-xl p-4 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 shadow-md'
              }`}
            >
              <div className="whitespace-pre-wrap space-y-2">
                {m.content}
              </div>

              {/* Citations & Evidence Drawer for Assistant replies */}
              {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-800/80">
                  <button
                    onClick={() => toggleSource(idx)}
                    className="flex items-center justify-between w-full text-xs font-medium text-cyan-400 hover:text-cyan-300 transition"
                  >
                    <span className="flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5" />
                      Verified Sources & Citations ({m.sources.length})
                    </span>
                    {expandedSources[idx] ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>

                  {expandedSources[idx] && (
                    <div className="mt-2.5 space-y-2 bg-slate-950/70 p-3 rounded-lg border border-slate-800/60">
                      {m.sources.map((src, sIdx) => (
                        <div key={sIdx} className="text-xs space-y-0.5">
                          <div className="flex items-center justify-between text-slate-300 font-semibold">
                            <span>{src.source}</span>
                            <span className="text-[10px] text-slate-400">{src.category}</span>
                          </div>
                          <p className="text-slate-400">{src.details}</p>
                          <div className="text-[10px] text-slate-400">Timestamp: {src.timestamp}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-3 text-cyan-400 text-sm py-2">
            <LoadingSpinner size="sm" />
            <span className="animate-pulse">Retrieving audited filings, market indicators & synthesizing response...</span>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 flex items-center gap-1 shrink-0 font-medium">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          Suggested:
        </span>
        {PRESET_PROMPTS.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(p)}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-slate-300 hover:text-white transition whitespace-nowrap disabled:opacity-50"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="bg-[#131B2E] border border-slate-800 rounded-xl p-2.5 flex items-center gap-3 shadow-lg">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
          placeholder={`Ask about ${selectedSymbol} (e.g. "Explain recent financial performance and debt risks")...`}
          disabled={loading}
          className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-400 outline-none"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputMessage.trim() || loading}
          className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-40 text-white font-medium rounded-lg text-sm flex items-center gap-2 transition shadow-md"
        >
          <Send className="w-4 h-4" />
          <span>Send</span>
        </button>
      </div>
    </div>
  );
};

export default ResearchAssistantPage;

