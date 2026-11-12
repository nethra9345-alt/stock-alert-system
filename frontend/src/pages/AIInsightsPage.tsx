import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Activity,
  ShieldAlert,
  Award,
  Zap,
  CheckCircle2,
  RefreshCw,
  Search,
  HelpCircle,
  Cpu,
} from 'lucide-react';
import { mlApi } from '../services/api';
import {
  StockPredictionResponse,
  ModelComparisonResponse,
  ModelInfoResponse,
} from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import Badge from '../components/Badge';

const POPULAR_SYMBOLS = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'];

export const AIInsightsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentSymbol = searchParams.get('symbol') || 'RELIANCE.NS';

  const [symbolInput, setSymbolInput] = useState(currentSymbol);
  const [prediction, setPrediction] = useState<StockPredictionResponse | null>(null);
  const [evaluation, setEvaluation] = useState<ModelComparisonResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchMLData(currentSymbol);
  }, [currentSymbol]);

  const fetchMLData = async (symbol: string) => {
    try {
      setLoading(true);
      setError(null);

      const [predRes, evalRes, infoRes] = await Promise.all([
        mlApi.getPrediction(symbol),
        mlApi.getEvaluation(symbol),
        mlApi.getModelInfo(),
      ]);

      setPrediction(predRes);
      setEvaluation(evalRes);
      setModelInfo(infoRes);
    } catch (err: any) {
      console.error('Error fetching ML insights:', err);
      setError(err?.response?.data?.detail || err?.message || `Failed to fetch ML insights for ${symbol}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRetrain = async () => {
    try {
      setRetraining(true);
      setInfoMessage(`Retraining Random Forest & XGBoost models on latest 2-year data for ${currentSymbol}...`);
      await mlApi.trainModels(currentSymbol, '2y');
      setInfoMessage(`Models successfully trained and updated for ${currentSymbol}!`);
      await fetchMLData(currentSymbol);
      setTimeout(() => setInfoMessage(null), 4000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Retraining failed');
    } finally {
      setRetraining(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbolInput.trim()) return;
    let sym = symbolInput.trim().toUpperCase();
    if (!sym.includes('.')) sym += '.NS';
    setSearchParams({ symbol: sym });
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return '—';
    return `₹${val.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    })}`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-5 h-5 text-cyan-400" />
            <span className="text-xs font-mono font-semibold text-cyan-400 tracking-wider uppercase">
              Quantitative Machine Learning Engine
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI Market Intelligence</h1>
          <p className="text-sm text-slate-400 mt-1">
            Multi-model algorithmic forecasting using Random Forest, XGBoost, and Persistence Benchmarks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRetrain}
            disabled={retraining}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${retraining ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{retraining ? 'Retraining Models...' : 'Retrain on 2Y Data'}</span>
          </button>
        </div>
      </div>

      {infoMessage && (
        <div className="p-3 bg-cyan-950/70 border border-cyan-800 text-cyan-300 text-xs rounded-lg font-mono">
          {infoMessage}
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => fetchMLData(currentSymbol)} />}

      {/* Symbol Selector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Enter stock symbol (e.g. TCS.NS)..."
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold"
          >
            Predict
          </button>
        </form>

        <div className="flex items-center gap-2 overflow-x-auto text-xs scrollbar-none">
          <span className="text-slate-500 font-mono text-[11px] whitespace-nowrap">Presets:</span>
          {POPULAR_SYMBOLS.map((sym) => (
            <button
              key={sym}
              onClick={() => {
                setSymbolInput(sym);
                setSearchParams({ symbol: sym });
              }}
              className={`px-2.5 py-1 rounded font-mono font-medium transition whitespace-nowrap ${
                currentSymbol === sym
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {sym.replace('.NS', '')}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <LoadingSpinner text={`Computing quantitative inference & out-of-sample metrics for ${currentSymbol}...`} />
        </div>
      ) : prediction ? (
        <div className="space-y-6">
          {/* Main Consensus Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-2xl font-bold font-mono text-white">{prediction.symbol}</h2>
                  <Badge variant={prediction.is_demo ? 'warning' : 'success'}>
                    {prediction.is_demo ? 'DEMO DATA' : 'LIVE FEED'}
                  </Badge>
                  <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-800">
                    Target: {prediction.target_date}
                  </span>
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  Current Close Price: <strong className="text-white">{formatCurrency(prediction.current_price)}</strong> (as of {prediction.as_of_date})
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div>
                  <span className="text-xs text-slate-400 font-mono uppercase block text-left md:text-right">
                    Consensus Predicted Price
                  </span>
                  <div className="text-3xl font-extrabold font-mono text-cyan-400">
                    {formatCurrency(prediction.consensus_predicted_price)}
                  </div>
                </div>

                <div className="border-l border-slate-800 pl-6">
                  <span className="text-xs text-slate-400 font-mono uppercase block text-left md:text-right">
                    Consensus Direction
                  </span>
                  <div
                    className={`text-lg font-bold font-mono flex items-center gap-1.5 px-3 py-1 rounded-lg mt-1 ${
                      prediction.consensus_predicted_direction === 'UP'
                        ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/60'
                        : 'bg-rose-950/50 text-rose-400 border border-rose-800/60'
                    }`}
                  >
                    {prediction.consensus_predicted_direction === 'UP' ? (
                      <TrendingUp className="w-5 h-5" />
                    ) : (
                      <TrendingDown className="w-5 h-5" />
                    )}
                    <span>{prediction.consensus_predicted_direction}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Confidence & Consensus summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 text-xs font-mono">
              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500 uppercase">Algorithm Confidence</span>
                <div className="text-base font-bold text-amber-400 mt-1">
                  {prediction.confidence_level} CONFIDENCE
                </div>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Determined by model directional agreement
                </p>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500 uppercase">Validation Methodology</span>
                <div className="text-base font-bold text-slate-200 mt-1">
                  Walk-Forward TimeSeries
                </div>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Chronological split with zero data leakage
                </p>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <span className="text-slate-500 uppercase">Target Horizon</span>
                <div className="text-base font-bold text-cyan-400 mt-1">
                  Next Trading Day (t+1)
                </div>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Strict single-step ahead continuous target
                </p>
              </div>
            </div>
          </div>

          {/* Model Breakdown Grid */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Individual Model Predictions (t+1)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(prediction.predictions).map(([modelKey, result]) => {
                const isUp = result.predicted_direction === 'UP';
                const isBaseline = modelKey.toLowerCase().includes('baseline');
                const isRF = modelKey.toLowerCase().includes('random');
                const isXGB = modelKey.toLowerCase().includes('xgboost');

                return (
                  <div
                    key={modelKey}
                    className={`p-5 rounded-xl border bg-slate-900 shadow-lg relative ${
                      isBaseline
                        ? 'border-slate-800 opacity-90'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="text-sm font-bold text-white font-mono">
                          {isRF && 'Random Forest Regressor'}
                          {isXGB && 'XGBoost Regressor'}
                          {isBaseline && 'Persistence Baseline'}
                        </h4>
                        <span className="text-[11px] text-slate-500 font-sans">
                          {isBaseline
                            ? 'Random walk benchmark P(t)'
                            : isRF
                            ? 'Non-linear bagging ensemble'
                            : 'Gradient boosted decision trees'}
                        </span>
                      </div>
                      <span
                        className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                          isUp
                            ? 'bg-emerald-950/50 text-emerald-400'
                            : 'bg-rose-950/50 text-rose-400'
                        }`}
                      >
                        {result.predicted_direction}
                      </span>
                    </div>

                    <div className="space-y-2 mt-4 pt-3 border-t border-slate-800 font-mono text-xs">
                      <div className="flex justify-between items-baseline">
                        <span className="text-slate-400">Target Forecast:</span>
                        <span className="text-lg font-bold text-white">
                          {formatCurrency(result.predicted_price)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Expected Change:</span>
                        <span
                          className={`font-semibold ${
                            result.expected_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {result.expected_change >= 0 ? '+' : ''}
                          {result.expected_change.toFixed(2)} ({result.expected_change_percent.toFixed(2)}%)
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Out-of-sample MAE:</span>
                        <span className="text-slate-300">₹{result.model_mae.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Directional Accuracy:</span>
                        <span className="text-cyan-400 font-semibold">
                          {(result.directional_accuracy_hist * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Out-of-Sample Performance Comparison */}
          {evaluation && (
            <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Award className="w-5 h-5 text-amber-400" />
                    Strict Out-of-Sample Model Benchmarks
                  </h3>
                  <p className="text-xs text-slate-400">
                    Evaluated on unseen historical test data ({evaluation.test_samples} trading days)
                  </p>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  Split: {evaluation.train_samples} Train / {evaluation.test_samples} Test
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400 bg-slate-950/40">
                      <th className="py-3 px-4 font-semibold">Model Name</th>
                      <th className="py-3 px-4 font-semibold text-right">MAE (Error in INR)</th>
                      <th className="py-3 px-4 font-semibold text-right">RMSE (INR)</th>
                      <th className="py-3 px-4 font-semibold text-right">Directional Accuracy</th>
                      <th className="py-3 px-4 font-semibold text-right">Walk-Forward Accuracy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    {Object.entries(evaluation.models).map(([key, summary]) => {
                      const isBestMAE = evaluation.best_model_by_mae === key;
                      const isBestDA = evaluation.best_model_by_directional_accuracy === key;

                      return (
                        <tr key={key} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-bold text-white">
                            <div className="flex items-center gap-2">
                              <span>{summary.model_name}</span>
                              {isBestMAE && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-sans">
                                  Lowest MAE
                                </span>
                              )}
                              {isBestDA && (
                                <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-sans">
                                  Top Accuracy
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] font-normal text-slate-400 font-sans">
                              {summary.description}
                            </div>
                          </td>

                          <td className="py-3.5 px-4 text-right font-semibold text-slate-200">
                            ₹{summary.test_metrics.mae.toFixed(2)}
                          </td>

                          <td className="py-3.5 px-4 text-right text-slate-300">
                            ₹{summary.test_metrics.rmse.toFixed(2)}
                          </td>

                          <td className="py-3.5 px-4 text-right font-bold text-emerald-400">
                            {(summary.test_metrics.directional_accuracy * 100).toFixed(2)}%
                          </td>

                          <td className="py-3.5 px-4 text-right text-cyan-300">
                            {summary.walk_forward_metrics
                              ? `${(summary.walk_forward_metrics.directional_accuracy * 100).toFixed(2)}%`
                              : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Feature Importance Section */}
          {evaluation && evaluation.models['random_forest']?.feature_importances && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Feature Importances (Random Forest Gini Impurity)
                  </h3>
                  <p className="text-xs text-slate-400">
                    Relative contribution of technical indicators to price forecasting
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                {Object.entries(evaluation.models['random_forest'].feature_importances)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 8)
                  .map(([feat, weight]) => {
                    const percent = (weight * 100).toFixed(1);
                    return (
                      <div key={feat} className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-slate-300">{feat}</span>
                          <span className="text-cyan-400 font-semibold">{percent}%</span>
                        </div>
                        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary-500 to-cyan-400 rounded-full"
                            style={{ width: `${Math.min(100, Math.max(5, parseFloat(percent) * 3))}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Leakage Safeguards & Methodology */}
          {modelInfo && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Data Integrity & Leakage Prevention Architecture
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300 font-mono">
                {modelInfo.data_leakage_safeguards.map((item, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-slate-950/40 rounded-lg">
                    <span className="text-cyan-400 font-bold">•</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Prominent Risk Disclaimer */}
          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-3 text-xs text-slate-400">
            <ShieldAlert className="w-6 h-6 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-200">Legal Risk Disclaimer:</span>{' '}
              {prediction.disclaimer ||
                'All forecasts generated by StockPulse AI are purely experimental mathematical models and do not constitute investment advice or guarantees of profit. Financial markets are subject to systematic risks.'}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default AIInsightsPage;

