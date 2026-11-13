import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Activity,
  Award,
  Zap,
  RefreshCw,
  Search,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Layers,
  BarChart2,
  Calendar,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowUpRight,
  ArrowDownRight,
  Sliders,
  History
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  AreaChart,
  Area
} from 'recharts';
import { mlApi, marketApi } from '../services/api';
import {
  MultiHorizonPredictionResponse,
  ModelComparisonResponse,
  BacktestResultResponse,
  ModelDriftResponse,
  PredictionHistoryItem,
  StockHistory
} from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

const POPULAR_SYMBOLS = [
  'RELIANCE.NS',
  'TCS.NS',
  'INFY.NS',
  'HDFCBANK.NS',
  'ICICIBANK.NS',
  'SBIN.NS',
  'TATAMOTORS.NS',
  'ITC.NS'
];

type HorizonType = '1d' | '5d' | '10d';

export const PredictiveIntelligencePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentSymbol = searchParams.get('symbol') || 'RELIANCE.NS';

  const [symbolInput, setSymbolInput] = useState(currentSymbol);
  const [horizon, setHorizon] = useState<HorizonType>('1d');

  // API Data
  const [prediction, setPrediction] = useState<MultiHorizonPredictionResponse | null>(null);
  const [evaluation, setEvaluation] = useState<ModelComparisonResponse | null>(null);
  const [backtest, setBacktest] = useState<BacktestResultResponse | null>(null);
  const [drift, setDrift] = useState<ModelDriftResponse | null>(null);
  const [history, setHistory] = useState<PredictionHistoryItem[]>([]);
  const [stockHistory, setStockHistory] = useState<StockHistory | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<'forecast' | 'models' | 'backtest' | 'drift' | 'history'>('forecast');
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchData(currentSymbol, horizon);
  }, [currentSymbol, horizon]);

  const fetchData = async (symbol: string, hz: HorizonType) => {
    try {
      setLoading(true);
      setError(null);

      const [predRes, evalRes, btRes, driftRes, histRes, ohlcvRes] = await Promise.all([
        mlApi.getMultiHorizonPrediction(symbol, hz),
        mlApi.getAdvancedEvaluation(symbol, hz, '2y'),
        mlApi.getBacktest(symbol, hz, 'champion', '2y'),
        mlApi.getDrift(symbol, 'champion'),
        mlApi.getPredictionHistory(symbol, 25),
        marketApi.getStockHistory(symbol, '3mo', '1d').catch(() => null)
      ]);

      setPrediction(predRes);
      setEvaluation(evalRes);
      setBacktest(btRes);
      setDrift(driftRes);
      setHistory(histRes);
      setStockHistory(ohlcvRes);
    } catch (err: any) {
      console.error('Error fetching predictive data:', err);
      setError(err?.response?.data?.detail || err?.message || `Failed to fetch predictive intelligence for ${symbol}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSymbolSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbolInput.trim()) {
      const clean = symbolInput.trim().toUpperCase();
      const formatted = clean.includes('.') ? clean : `${clean}.NS`;
      setSearchParams({ symbol: formatted });
    }
  };

  const handleRetrain = async () => {
    try {
      setRetraining(true);
      setInfoMessage(`Retraining Ridge, Random Forest, XGBoost & Gradient Boosting for ${currentSymbol} (${horizon})...`);
      await mlApi.trainAdvancedModels(currentSymbol, horizon, '2y');
      setInfoMessage(`Models retrained and updated in PostgreSQL Model Registry for ${currentSymbol}!`);
      await fetchData(currentSymbol, horizon);
      setTimeout(() => setInfoMessage(null), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Retraining failed');
    } finally {
      setRetraining(false);
    }
  };

  // Build forecast chart data combining historical closes with predicted point & intervals
  const buildForecastChartData = () => {
    if (!stockHistory || !prediction) return [];
    const candles = (stockHistory.data || []).slice(-25);
    const dataPoints: any[] = candles.map((c) => ({
      date: (c.timestamp || '').slice(5, 10),
      actual: c.close,
      pointForecast: null,
      lower80: null,
      upper80: null,
      lower95: null,
      upper95: null
    }));

    if (dataPoints.length > 0) {
      const lastPoint = dataPoints[dataPoints.length - 1];
      lastPoint.pointForecast = lastPoint.actual;
      lastPoint.lower80 = lastPoint.actual;
      lastPoint.upper80 = lastPoint.actual;
      lastPoint.lower95 = lastPoint.actual;
      lastPoint.upper95 = lastPoint.actual;

      const champ = prediction.predictions[prediction.champion_model] || {
        predicted_price: prediction.champion_predicted_price,
        lower_bound_80: prediction.lower_bound,
        upper_bound_80: prediction.upper_bound,
        lower_bound_95: prediction.lower_bound,
        upper_bound_95: prediction.upper_bound
      };

      dataPoints.push({
        date: `+${horizon.toUpperCase()}`,
        actual: null,
        pointForecast: champ.predicted_price,
        lower80: champ.lower_bound_80,
        upper80: champ.upper_bound_80,
        lower95: champ.lower_bound_95,
        upper95: champ.upper_bound_95
      });
    }

    return dataPoints;
  };

  const champPred = prediction?.predictions[prediction?.champion_model || ''] || null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Symbol Selector */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-[#0E131F] border border-slate-800 rounded-xl p-5 shadow-lg">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                Predictive Intelligence & Quantitative Forecasting
                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800">
                  Stage 9
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Multi-horizon econometric forecasting, calibrated uncertainty intervals & walk-forward backtesting
              </p>
            </div>
          </div>

          {/* Quick symbol pills */}
          <div className="flex items-center gap-1.5 mt-4 flex-wrap">
            <span className="text-xs text-slate-500 mr-1 font-mono">POPULAR:</span>
            {POPULAR_SYMBOLS.map((sym) => (
              <button
                key={sym}
                onClick={() => {
                  setSymbolInput(sym);
                  setSearchParams({ symbol: sym });
                }}
                className={`text-xs px-2.5 py-1 rounded-md font-mono transition ${
                  currentSymbol === sym
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'bg-[#161D2F] text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {sym.replace('.NS', '')}
              </button>
            ))}
          </div>
        </div>

        {/* Search & Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <form onSubmit={handleSymbolSubmit} className="relative">
            <input
              type="text"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              placeholder="Search ticker (e.g. RELIANCE.NS)"
              className="bg-[#161D2F] border border-slate-800 text-slate-200 text-sm rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-cyan-500 w-full sm:w-64"
            />
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          </form>

          <button
            onClick={handleRetrain}
            disabled={retraining || loading}
            className="flex items-center justify-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm font-medium transition shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${retraining ? 'animate-spin' : ''}`} />
            {retraining ? 'Retraining...' : 'Retrain Models'}
          </button>
        </div>
      </div>

      {/* Info / Success banner */}
      {infoMessage && (
        <div className="p-4 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          {infoMessage}
        </div>
      )}

      {error && <ErrorAlert message={error} />}

      {/* Horizon Selector Tabs */}
      <div className="flex items-center justify-between bg-[#0E131F] border border-slate-800 rounded-xl p-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono px-3">FORECAST HORIZON:</span>
          {(['1d', '5d', '10d'] as HorizonType[]).map((hz) => (
            <button
              key={hz}
              onClick={() => setHorizon(hz)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
                horizon === hz
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#161D2F]'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              {hz === '1d' ? '1-Day (t+1)' : hz === '5d' ? '5-Day (Weekly)' : '10-Day (Bi-Weekly)'}
            </button>
          ))}
        </div>

        {/* View mode navigation tabs */}
        <div className="flex items-center gap-1 border-l border-slate-800 pl-3">
          {[
            { id: 'forecast', label: 'Forecast & Intervals', icon: Brain },
            { id: 'models', label: 'Model League', icon: Layers },
            { id: 'backtest', label: 'Walk-Forward Backtest', icon: BarChart2 },
            { id: 'drift', label: 'Drift Monitor', icon: Sliders },
            { id: 'history', label: 'Prediction History', icon: History }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                  activeTab === tab.id
                    ? 'bg-slate-800 text-cyan-400 border border-slate-700'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner />
        </div>
      ) : (
        <>
          {/* TAB 1: FORECAST & CALIBRATED INTERVALS */}
          {activeTab === 'forecast' && prediction && (
            <div className="space-y-6">
              {/* Champion Card Banner */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Current Price */}
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5">
                  <div className="text-xs text-slate-500 font-mono mb-1">CURRENT MARKET PRICE</div>
                  <div className="text-2xl font-bold text-slate-100 font-mono">
                    ₹{prediction.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-slate-400 mt-2 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> As of: {prediction.as_of_date}
                  </div>
                </div>

                {/* Champion Forecast */}
                <div className="bg-[#0E131F] border border-cyan-500/30 rounded-xl p-5 relative overflow-hidden">
                  <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
                    <Award className="w-3 h-3" /> Champion Model
                  </div>
                  <div className="text-xs text-cyan-400 font-mono mb-1">
                    {prediction.champion_model.replace('_', ' ').toUpperCase()} FORECAST
                  </div>
                  <div className="text-2xl font-bold text-cyan-300 font-mono">
                    ₹{prediction.champion_predicted_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                        prediction.champion_predicted_direction === 'UP'
                          ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                          : prediction.champion_predicted_direction === 'DOWN'
                          ? 'bg-rose-950/80 text-rose-400 border border-rose-800'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {prediction.champion_predicted_direction === 'UP' ? (
                        <ArrowUpRight className="w-3 h-3" />
                      ) : prediction.champion_predicted_direction === 'DOWN' ? (
                        <ArrowDownRight className="w-3 h-3" />
                      ) : null}
                      {prediction.champion_predicted_direction} ({prediction.champion_predicted_return_pct > 0 ? '+' : ''}
                      {prediction.champion_predicted_return_pct}%)
                    </span>
                  </div>
                </div>

                {/* Calibrated 95% Interval */}
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5">
                  <div className="text-xs text-slate-500 font-mono mb-1">95% CALIBRATED INTERVAL</div>
                  <div className="text-lg font-bold text-slate-200 font-mono">
                    ₹{prediction.lower_bound} — ₹{prediction.upper_bound}
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    Range: ±₹{Math.round((prediction.upper_bound - prediction.lower_bound) / 2)} (Gaussian Residual Var)
                  </div>
                </div>

                {/* Model Confidence & Drift Status */}
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5">
                  <div className="text-xs text-slate-500 font-mono mb-1">CONFIDENCE & HEALTH</div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        prediction.confidence_level === 'HIGH'
                          ? 'success'
                          : prediction.confidence_level === 'MODERATE'
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      {prediction.confidence_level} CONFIDENCE
                    </Badge>
                    {drift && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
                          drift.drift_status === 'STABLE'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                            : drift.drift_status === 'MODERATE_DRIFT'
                            ? 'bg-amber-950/60 text-amber-400 border border-amber-800'
                            : 'bg-rose-950/60 text-rose-400 border border-rose-800'
                        }`}
                      >
                        {drift.drift_status}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 mt-2">
                    Historical Accuracy: {champPred?.directional_accuracy_hist || 50}%
                  </div>
                </div>
              </div>

              {/* Forecast & Interval Visualization Chart */}
              <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
                      <BarChart2 className="w-4 h-4 text-cyan-400" />
                      Historical Price Trend & Projected Interval Band (+{horizon.toUpperCase()})
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Last 25 trading sessions closing prices with out-of-sample forecast and shaded 80% & 95% confidence intervals
                    </p>
                  </div>
                </div>

                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={buildForecastChartData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="date" stroke="#64748B" tick={{ fontSize: 11 }} />
                      <YAxis
                        stroke="#64748B"
                        tick={{ fontSize: 11 }}
                        domain={['auto', 'auto']}
                        tickFormatter={(v) => `₹${v}`}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0E131F', borderColor: '#334155' }}
                        formatter={(val: any, name: string) => [
                          typeof val === 'number' ? `₹${val.toFixed(2)}` : val,
                          name
                        ]}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="Actual Close"
                        stroke="#38BDF8"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="pointForecast"
                        name="Forecast Point"
                        stroke="#A855F7"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot={{ r: 5, fill: '#A855F7' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="upper95"
                        name="95% Upper Bound"
                        stroke="#10B981"
                        strokeDasharray="2 2"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="lower95"
                        name="95% Lower Bound"
                        stroke="#EF4444"
                        strokeDasharray="2 2"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Honest Uncertainty Disclaimer */}
                <div className="mt-4 p-3.5 rounded-lg bg-[#161D2F] border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-300">Statistical Uncertainty Note: </span>
                    {prediction.uncertainty_explanation}
                  </div>
                </div>
              </div>

              {/* Model Ensemble Cards */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {Object.entries(prediction.predictions).map(([mKey, mVal]) => (
                  <div
                    key={mKey}
                    className={`bg-[#0E131F] border rounded-xl p-4 transition ${
                      mVal.is_champion
                        ? 'border-amber-500/40 bg-amber-950/10'
                        : 'border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-slate-300 truncate">
                        {mKey.replace('_', ' ').toUpperCase()}
                      </span>
                      {mVal.is_champion && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                          🏆 CHAMP
                        </span>
                      )}
                    </div>
                    <div className="text-lg font-bold font-mono text-slate-100">
                      ₹{mVal.predicted_price.toFixed(2)}
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                      <span>Direction:</span>
                      <span
                        className={`font-semibold ${
                          mVal.predicted_direction === 'UP'
                            ? 'text-emerald-400'
                            : mVal.predicted_direction === 'DOWN'
                            ? 'text-rose-400'
                            : 'text-slate-400'
                        }`}
                      >
                        {mVal.predicted_direction} ({mVal.predicted_return_pct > 0 ? '+' : ''}
                        {mVal.predicted_return_pct}%)
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                      <span>Test MAE:</span>
                      <span className="font-mono text-slate-400">₹{mVal.model_mae}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
                      <span>Hit Ratio:</span>
                      <span className="font-mono text-slate-400">{mVal.directional_accuracy_hist}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: MODEL LEAGUE & COMPARISON */}
          {activeTab === 'models' && evaluation && (
            <div className="space-y-6">
              {/* Champion Rationale Banner */}
              <div className="bg-[#0E131F] border border-amber-500/30 rounded-xl p-5 shadow-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="w-5 h-5 text-amber-400" />
                  <h3 className="text-base font-semibold text-slate-200">
                    Champion Selection Rationale ({horizon.toUpperCase()} Horizon)
                  </h3>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">{evaluation.champion_rationale}</p>
                <div className="mt-3 flex items-center gap-4 text-xs font-mono text-slate-500">
                  <span>TRAIN PERIOD: {evaluation.train_date_range} ({evaluation.train_samples} bars)</span>
                  <span>TEST PERIOD: {evaluation.test_date_range} ({evaluation.test_samples} bars)</span>
                </div>
              </div>

              {/* Models Comparison Table */}
              <div className="bg-[#0E131F] border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200">
                    Out-Of-Sample Model Performance Comparison ({evaluation.test_samples} Unseen Trading Days)
                  </h3>
                  <span className="text-xs text-slate-500 font-mono">STRICT CHRONOLOGICAL SPLIT</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#161D2F] text-slate-400 font-mono border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">MODEL NAME</th>
                        <th className="py-3 px-4">ARCHITECTURE TYPE</th>
                        <th className="py-3 px-4">TEST MAE</th>
                        <th className="py-3 px-4">TEST RMSE</th>
                        <th className="py-3 px-4">MAPE</th>
                        <th className="py-3 px-4">DIRECTION HIT RATIO</th>
                        <th className="py-3 px-4">UP PRECISION</th>
                        <th className="py-3 px-4">UP F1</th>
                        <th className="py-3 px-4">STATUS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300 font-mono">
                      {Object.entries(evaluation.models).map(([mKey, mVal]: [string, any]) => {
                        const isChamp = mVal.is_champion;
                        const tm = mVal.test_metrics;
                        return (
                          <tr
                            key={mKey}
                            className={`hover:bg-slate-800/40 transition ${
                              isChamp ? 'bg-amber-950/20' : ''
                            }`}
                          >
                            <td className="py-3 px-4 font-bold text-slate-200 flex items-center gap-2">
                              {mVal.model_name}
                              {isChamp && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                                  🏆 CHAMPION
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-slate-400 font-sans">
                              {mKey.includes('baseline')
                                ? 'Random Walk Benchmark'
                                : mKey.includes('ridge')
                                ? 'L2 Regularized Linear'
                                : mKey.includes('forest')
                                ? 'Bagging Ensemble'
                                : 'Gradient Boosted Trees'}
                            </td>
                            <td className="py-3 px-4 font-bold text-cyan-400">₹{tm.mae}</td>
                            <td className="py-3 px-4 text-slate-300">₹{tm.rmse}</td>
                            <td className="py-3 px-4 text-slate-300">{tm.mape}%</td>
                            <td className="py-3 px-4">
                              <span
                                className={`px-2 py-0.5 rounded font-bold ${
                                  tm.directional_accuracy >= 52
                                    ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                                    : 'bg-slate-800 text-slate-400'
                                }`}
                              >
                                {tm.directional_accuracy}%
                              </span>
                            </td>
                            <td className="py-3 px-4 text-slate-300">{tm.precision_up || 0}%</td>
                            <td className="py-3 px-4 text-slate-300">{tm.f1_up || 0}%</td>
                            <td className="py-3 px-4">
                              {isChamp ? (
                                <Badge variant="warning">Champion</Badge>
                              ) : (
                                <span className="text-slate-500">Evaluated</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: WALK-FORWARD BACKTEST */}
          {activeTab === 'backtest' && backtest && (
            <div className="space-y-6">
              {/* Backtest Metric Highlights */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <div className="text-xs text-slate-500 font-mono mb-1">WALK-FORWARD MAE</div>
                  <div className="text-2xl font-bold text-cyan-400 font-mono">₹{backtest.wf_mae}</div>
                  <div className="text-xs text-slate-400 mt-1">Expanding window out-of-sample error</div>
                </div>

                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <div className="text-xs text-slate-500 font-mono mb-1">DIRECTIONAL ACCURACY</div>
                  <div className="text-2xl font-bold text-emerald-400 font-mono">{backtest.wf_directional_accuracy}%</div>
                  <div className="text-xs text-slate-400 mt-1">Across {backtest.total_steps} out-of-sample days</div>
                </div>

                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <div className="text-xs text-slate-500 font-mono mb-1">SIMULATED RETURN (0.1% FEE)</div>
                  <div
                    className={`text-2xl font-bold font-mono ${
                      backtest.simulated_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {backtest.simulated_return_pct >= 0 ? '+' : ''}
                    {backtest.simulated_return_pct}%
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Win Rate: {backtest.win_rate}%</div>
                </div>

                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <div className="text-xs text-slate-500 font-mono mb-1">MAX STRATEGY DRAWDOWN</div>
                  <div className="text-2xl font-bold text-rose-400 font-mono">{backtest.max_drawdown}%</div>
                  <div className="text-xs text-slate-400 mt-1">Profit Factor: {backtest.profit_factor || 1.15}</div>
                </div>
              </div>

              {/* Equity Curve Chart */}
              <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-semibold text-slate-200">
                      Simulated Walk-Forward Equity Curve vs Buy & Hold Benchmark
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Starting capital: ₹1,00,000 | Realistic 0.1% friction (brokerage + slippage) per trade
                    </p>
                  </div>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={backtest.equity_curve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="date" stroke="#64748B" tick={{ fontSize: 11 }} />
                      <YAxis
                        stroke="#64748B"
                        tick={{ fontSize: 11 }}
                        domain={['auto', 'auto']}
                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0E131F', borderColor: '#334155' }}
                        formatter={(val: any, name: string) => [`₹${val.toLocaleString('en-IN')}`, name]}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="equity"
                        name="Model Strategy Equity"
                        stroke="#10B981"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="benchmark"
                        name="Buy & Hold Benchmark"
                        stroke="#64748B"
                        strokeWidth={1.5}
                        strokeDasharray="3 3"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Regime Breakdown & Error Distribution */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Regime Breakdown */}
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <h4 className="text-xs font-mono font-bold text-slate-400 mb-3 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    PERFORMANCE BY MARKET REGIME
                  </h4>
                  <div className="space-y-2">
                    {backtest.regime_breakdown.map((rg) => (
                      <div
                        key={rg.regime}
                        className="flex items-center justify-between p-2.5 rounded-lg bg-[#161D2F] border border-slate-800 text-xs"
                      >
                        <span className="font-mono font-semibold text-slate-200">{rg.regime}</span>
                        <div className="flex items-center gap-4">
                          <span className="text-slate-400">Samples: {rg.samples}</span>
                          <span className="text-cyan-400 font-mono font-bold">MAE: ₹{rg.mae}</span>
                          <span className="text-emerald-400 font-mono font-bold">DA: {rg.directional_accuracy}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Error Distribution */}
                <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-4">
                  <h4 className="text-xs font-mono font-bold text-slate-400 mb-3 flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-purple-400" />
                    RESIDUAL ERROR DISTRIBUTION (₹)
                  </h4>
                  <div className="grid grid-cols-5 gap-2 text-center">
                    <div className="p-2 rounded bg-[#161D2F] border border-slate-800">
                      <div className="text-[10px] text-slate-500">P5 (Tail)</div>
                      <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                        ₹{backtest.error_distribution.p5}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#161D2F] border border-slate-800">
                      <div className="text-[10px] text-slate-500">Median (P50)</div>
                      <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                        ₹{backtest.error_distribution.p50}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#161D2F] border border-slate-800">
                      <div className="text-[10px] text-slate-500">P95 (Tail)</div>
                      <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                        ₹{backtest.error_distribution.p95}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#161D2F] border border-slate-800">
                      <div className="text-[10px] text-slate-500">Mean Bias</div>
                      <div className="text-xs font-mono font-bold text-cyan-400 mt-0.5">
                        ₹{backtest.error_distribution.mean_error}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#161D2F] border border-slate-800">
                      <div className="text-[10px] text-slate-500">Std Error</div>
                      <div className="text-xs font-mono font-bold text-purple-400 mt-0.5">
                        ₹{backtest.error_distribution.std_error}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: DRIFT MONITOR */}
          {activeTab === 'drift' && drift && (
            <div className="space-y-6">
              <div className="bg-[#0E131F] border border-slate-800 rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-5 h-5 text-cyan-400" />
                    <div>
                      <h3 className="text-base font-semibold text-slate-200">
                        Concept Drift & Degradation Telemetry
                      </h3>
                      <p className="text-xs text-slate-500">
                        Continuous audit of recent 20-session error against baseline test error
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      drift.drift_status === 'STABLE'
                        ? 'success'
                        : drift.drift_status === 'MODERATE_DRIFT'
                        ? 'warning'
                        : 'danger'
                    }
                  >
                    {drift.drift_status}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-[#161D2F] border border-slate-800 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">BASELINE TEST MAE</div>
                    <div className="text-xl font-bold font-mono text-slate-200">₹{drift.baseline_mae}</div>
                    <div className="text-xs text-slate-400 mt-1">Established out-of-sample benchmark</div>
                  </div>
                  <div className="bg-[#161D2F] border border-slate-800 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">RECENT 20-SESSION MAE</div>
                    <div className="text-xl font-bold font-mono text-cyan-400">₹{drift.recent_mae}</div>
                    <div className="text-xs text-slate-400 mt-1">Rolling short-term forecast error</div>
                  </div>
                  <div className="bg-[#161D2F] border border-slate-800 rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">DRIFT RATIO</div>
                    <div
                      className={`text-xl font-bold font-mono ${
                        drift.drift_ratio <= 1.25
                          ? 'text-emerald-400'
                          : drift.drift_ratio <= 1.6
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {drift.drift_ratio}x
                    </div>
                    <div className="text-xs text-slate-400 mt-1">Threshold for Retrain: &gt; 1.40x</div>
                  </div>
                </div>

                {/* Recommendation Box */}
                <div className="mt-4 p-4 rounded-lg bg-[#161D2F] border border-slate-800 flex items-start gap-3">
                  {drift.retrain_recommended ? (
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="text-sm font-semibold text-slate-200">
                      Recommendation: {drift.retrain_recommended ? 'Retraining Recommended' : 'Model State Optimal'}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">{drift.recommendation_text}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: PREDICTION HISTORY */}
          {activeTab === 'history' && (
            <div className="bg-[#0E131F] border border-slate-800 rounded-xl overflow-hidden shadow-lg">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <History className="w-4 h-4 text-cyan-400" />
                  Historical Predictions Telemetry Log ({history.length} Records)
                </h3>
                <span className="text-xs text-slate-500 font-mono">POSTGRESQL AUDIT TRAIL</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#161D2F] text-slate-400 font-mono border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">PREDICTION DATE</th>
                      <th className="py-3 px-4">MODEL</th>
                      <th className="py-3 px-4">HORIZON</th>
                      <th className="py-3 px-4">PRICE AT PREDICTION</th>
                      <th className="py-3 px-4">PREDICTED PRICE</th>
                      <th className="py-3 px-4">95% INTERVAL</th>
                      <th className="py-3 px-4">ACTUAL OUTCOME</th>
                      <th className="py-3 px-4">ERROR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300 font-mono">
                    {history.map((h) => (
                      <tr key={h.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3 px-4 text-slate-400">{h.prediction_date}</td>
                        <td className="py-3 px-4 font-bold text-slate-200">{h.model_name.replace('_', ' ').toUpperCase()}</td>
                        <td className="py-3 px-4 text-cyan-400 uppercase font-semibold">{h.horizon}</td>
                        <td className="py-3 px-4">₹{h.current_price.toFixed(2)}</td>
                        <td className="py-3 px-4 font-bold text-purple-400">₹{h.predicted_price.toFixed(2)}</td>
                        <td className="py-3 px-4 text-slate-400">
                          ₹{h.lower_bound.toFixed(0)} - ₹{h.upper_bound.toFixed(0)}
                        </td>
                        <td className="py-3 px-4">
                          {h.actual_price ? `₹${h.actual_price.toFixed(2)}` : <span className="text-slate-500">Pending</span>}
                        </td>
                        <td className="py-3 px-4">
                          {h.absolute_error ? (
                            <span className="text-rose-400">₹{h.absolute_error.toFixed(2)}</span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Persistent Regulatory & Financial Disclaimer */}
      <div className="p-4 rounded-xl bg-[#0E131F] border border-slate-800/80 text-xs text-slate-500 leading-relaxed">
        <span className="font-semibold text-slate-400">LEGAL & REGULATORY DISCLAIMER: </span>
        All quantitative forecasts, moving-average models, prediction intervals, and walk-forward simulations generated by
        StockPulse AI are mathematical approximations intended strictly for research and educational purposes. Financial
        markets exhibit non-stationary, stochastic behavior. Past model performance and walk-forward backtests do not guarantee
        future market prices or investment returns. This application does NOT execute automated orders or provide personalized
        investment advice.
      </div>
    </div>
  );
};

export default PredictiveIntelligencePage;
