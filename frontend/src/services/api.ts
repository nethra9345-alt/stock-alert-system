import axios, { AxiosInstance } from 'axios';
import {
  HealthResponse,
  MarketOverview,
  IndexQuote,
  StockQuote,
  StockHistory,
  TechnicalIndicatorResponse,
  WatchlistItem,
  PortfolioOverview,
  PortfolioTransaction,
  PortfolioAnalytics,
  PortfolioRiskAnalysis,
  PriceAlert,
  AlertHistoryItem,
  AlertPreferences,
  AlertEvaluateResponse,
  StockPredictionResponse,
  ModelComparisonResponse,
  ModelInfoResponse,
  CompanyFundamentals,
  TechnicalAnalysis,
  StockComparison,
  ResearchChatMessageItem,
  ResearchReportItem,
  NewsItem,
  CompanySentimentSummary,
  SentimentTimelinePoint,
  NewsCorrelation,
  MarketNewsOverview,
  NewsAlertItem,
  MultiHorizonPredictionResponse,
  AdvancedModelComparisonResponse,
  BacktestResultResponse,
  ModelDriftResponse,
  PredictionHistoryItem,
  UserProfile,
  AuthTokenResponse
} from '../types';

// Use VITE_API_BASE_URL if configured, otherwise default to '/api' for Vite dev proxy
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization Bearer token to all outgoing requests if session exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('stockpulse_access_token') || sessionStorage.getItem('stockpulse_access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global response interceptor for session expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const hadToken = !!(localStorage.getItem('stockpulse_access_token') || sessionStorage.getItem('stockpulse_access_token'));
      if (hadToken && !error.config.url?.includes('/auth/login')) {
        localStorage.removeItem('stockpulse_access_token');
        sessionStorage.removeItem('stockpulse_access_token');
        localStorage.removeItem('stockpulse_user');
      }
    }
    return Promise.reject(error);
  }
);

export const marketApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const res = await api.get<HealthResponse>('/health');
    return res.data;
  },

  getOverview: async (): Promise<MarketOverview> => {
    const res = await api.get<MarketOverview>('/market/overview');
    return res.data;
  },

  getIndices: async (): Promise<IndexQuote[]> => {
    const res = await api.get<IndexQuote[]>('/market/indices');
    return res.data;
  },

  getStockQuote: async (symbol: string): Promise<StockQuote> => {
    const res = await api.get<StockQuote>(`/stocks/${encodeURIComponent(symbol)}`);
    return res.data;
  },

  getStockHistory: async (
    symbol: string,
    period: string = '6mo',
    interval: string = '1d'
  ): Promise<StockHistory> => {
    const res = await api.get<StockHistory>(`/stocks/${encodeURIComponent(symbol)}/history`, {
      params: { period, interval },
    });
    return res.data;
  },

  getStockIndicators: async (
    symbol: string,
    period: string = '1y'
  ): Promise<TechnicalIndicatorResponse> => {
    const res = await api.get<TechnicalIndicatorResponse>(
      `/stocks/${encodeURIComponent(symbol)}/indicators`,
      { params: { period } }
    );
    return res.data;
  },
};

export const watchlistApi = {
  getWatchlist: async (): Promise<WatchlistItem[]> => {
    const res = await api.get<WatchlistItem[]>('/watchlist');
    return res.data;
  },

  addStock: async (symbol: string, notes?: string, companyName?: string): Promise<WatchlistItem> => {
    const res = await api.post<WatchlistItem>('/watchlist', {
      symbol,
      notes,
      company_name: companyName,
      exchange: symbol.endsWith('.BO') ? 'BSE' : 'NSE',
    });
    return res.data;
  },

  updateItem: async (id: number, notes?: string, companyName?: string): Promise<WatchlistItem> => {
    const res = await api.put<WatchlistItem>(`/watchlist/${id}`, {
      notes,
      company_name: companyName,
    });
    return res.data;
  },

  removeStock: async (id: number): Promise<{ status: string; message: string }> => {
    const res = await api.delete<{ status: string; message: string }>(`/watchlist/${id}`);
    return res.data;
  },
};

export const portfolioApi = {
  getPortfolio: async (): Promise<PortfolioOverview> => {
    const res = await api.get<PortfolioOverview>('/portfolio');
    return res.data;
  },

  getAnalytics: async (): Promise<PortfolioAnalytics> => {
    const res = await api.get<PortfolioAnalytics>('/portfolio/analytics');
    return res.data;
  },

  getPerformance: async (): Promise<any> => {
    const res = await api.get('/portfolio/performance');
    return res.data;
  },

  getAllocation: async (): Promise<any> => {
    const res = await api.get('/portfolio/allocation');
    return res.data;
  },

  getRisk: async (period: string = '6mo'): Promise<PortfolioRiskAnalysis> => {
    const res = await api.get<PortfolioRiskAnalysis>('/portfolio/risk', {
      params: { period },
    });
    return res.data;
  },

  getTransactions: async (): Promise<PortfolioTransaction[]> => {
    const res = await api.get<PortfolioTransaction[]>('/portfolio/transactions');
    return res.data;
  },

  addTransaction: async (data: {
    symbol: string;
    company_name?: string;
    exchange?: string;
    transaction_type: 'BUY' | 'SELL';
    quantity: number;
    purchase_price: number;
    notes?: string;
  }): Promise<PortfolioTransaction> => {
    const res = await api.post<PortfolioTransaction>('/portfolio/transaction', data);
    return res.data;
  },

  deleteTransaction: async (id: number): Promise<{ status: string; message: string }> => {
    const res = await api.delete<{ status: string; message: string }>(`/portfolio/transaction/${id}`);
    return res.data;
  },
};

export const alertsApi = {
  getAlerts: async (): Promise<PriceAlert[]> => {
    const res = await api.get<PriceAlert[]>('/alerts');
    return res.data;
  },

  createAlert: async (data: {
    symbol: string;
    company_name?: string;
    target_price: number;
    condition: 'ABOVE' | 'BELOW';
    notes?: string;
  }): Promise<PriceAlert> => {
    const res = await api.post<PriceAlert>('/alerts', data);
    return res.data;
  },

  toggleAlert: async (id: number): Promise<PriceAlert> => {
    const res = await api.patch<PriceAlert>(`/alerts/${id}/toggle`);
    return res.data;
  },

  deleteAlert: async (id: number): Promise<{ status: string; message: string }> => {
    const res = await api.delete<{ status: string; message: string }>(`/alerts/${id}`);
    return res.data;
  },

  getHistory: async (status?: string, limit: number = 50): Promise<AlertHistoryItem[]> => {
    const res = await api.get<AlertHistoryItem[]>('/alerts/history', {
      params: { status, limit },
    });
    return res.data;
  },

  acknowledgeAlert: async (id: number): Promise<AlertHistoryItem> => {
    const res = await api.post<AlertHistoryItem>(`/alerts/history/${id}/acknowledge`);
    return res.data;
  },

  resolveAlert: async (id: number): Promise<AlertHistoryItem> => {
    const res = await api.post<AlertHistoryItem>(`/alerts/history/${id}/resolve`);
    return res.data;
  },

  getPreferences: async (): Promise<AlertPreferences> => {
    const res = await api.get<AlertPreferences>('/alerts/preferences');
    return res.data;
  },

  updatePreferences: async (data: Partial<AlertPreferences>): Promise<AlertPreferences> => {
    const res = await api.put<AlertPreferences>('/alerts/preferences', data);
    return res.data;
  },

  evaluateAlerts: async (): Promise<AlertEvaluateResponse> => {
    const res = await api.post<AlertEvaluateResponse>('/alerts/evaluate');
    return res.data;
  },
};

export const mlApi = {
  getModelInfo: async (): Promise<ModelInfoResponse> => {
    const res = await api.get<ModelInfoResponse>('/ml/models');
    return res.data;
  },

  getPrediction: async (symbol: string): Promise<StockPredictionResponse> => {
    const res = await api.get<StockPredictionResponse>(`/ml/predict/${encodeURIComponent(symbol)}`);
    return res.data;
  },

  getEvaluation: async (symbol: string, period: string = '2y'): Promise<ModelComparisonResponse> => {
    const res = await api.get<ModelComparisonResponse>(
      `/ml/evaluate/${encodeURIComponent(symbol)}`,
      { params: { period } }
    );
    return res.data;
  },

  trainModels: async (symbol: string, period: string = '2y'): Promise<ModelComparisonResponse> => {
    const res = await api.post<ModelComparisonResponse>(
      `/ml/train/${encodeURIComponent(symbol)}`,
      null,
      { params: { period } }
    );
    return res.data;
  },

  getMultiHorizonPrediction: async (
    symbol: string,
    horizon: string = '1d'
  ): Promise<MultiHorizonPredictionResponse> => {
    const res = await api.get<MultiHorizonPredictionResponse>(
      `/ml/predict/${encodeURIComponent(symbol)}`,
      { params: { horizon } }
    );
    return res.data;
  },

  getAdvancedEvaluation: async (
    symbol: string,
    horizon: string = '1d',
    period: string = '2y'
  ): Promise<ModelComparisonResponse> => {
    const res = await api.get<ModelComparisonResponse>(
      `/ml/evaluate/${encodeURIComponent(symbol)}`,
      { params: { horizon, period } }
    );
    return res.data;
  },

  trainAdvancedModels: async (
    symbol: string,
    horizon: string = '1d',
    period: string = '2y'
  ): Promise<ModelComparisonResponse> => {
    const res = await api.post<ModelComparisonResponse>(
      `/ml/train/${encodeURIComponent(symbol)}`,
      null,
      { params: { horizon, period } }
    );
    return res.data;
  },

  getBacktest: async (
    symbol: string,
    horizon: string = '1d',
    modelName: string = 'champion',
    period: string = '2y'
  ): Promise<BacktestResultResponse> => {
    const res = await api.get<BacktestResultResponse>(
      `/ml/backtest/${encodeURIComponent(symbol)}`,
      { params: { horizon, model_name: modelName, period } }
    );
    return res.data;
  },

  getDrift: async (
    symbol: string,
    modelName: string = 'champion'
  ): Promise<ModelDriftResponse> => {
    const res = await api.get<ModelDriftResponse>(
      `/ml/drift/${encodeURIComponent(symbol)}`,
      { params: { model_name: modelName } }
    );
    return res.data;
  },

  getPredictionHistory: async (
    symbol: string,
    limit: number = 50
  ): Promise<PredictionHistoryItem[]> => {
    const res = await api.get<PredictionHistoryItem[]>(
      `/ml/prediction-history/${encodeURIComponent(symbol)}`,
      { params: { limit } }
    );
    return res.data;
  },
};

export const eventsApi = {
  getEvents: async (params?: {
    symbol?: string;
    event_type?: string;
    severity?: string;
    is_verified?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ count: number; events: any[] }> => {
    const res = await api.get('/events', { params });
    return res.data;
  },

  getEventsForSymbol: async (
    symbol: string,
    params?: { event_type?: string; limit?: number }
  ): Promise<{ count: number; events: any[] }> => {
    const res = await api.get(`/events/${encodeURIComponent(symbol)}`, {
      params,
    });
    return res.data;
  },

  getLatestEvent: async (symbol: string): Promise<any> => {
    const res = await api.get(`/events/${encodeURIComponent(symbol)}/latest`);
    return res.data;
  },

  analyzeEvents: async (
    symbol: string,
    period: string = '6mo',
    priceThresholdPct: number = 3.5,
    volumeRatioThreshold: number = 2.5
  ): Promise<any> => {
    const res = await api.post(`/events/${encodeURIComponent(symbol)}/analyze`, {
      period,
      price_threshold_pct: priceThresholdPct,
      volume_ratio_threshold: volumeRatioThreshold,
    });
    return res.data;
  },
};

export const researchApi = {
  getDossier: async (symbol: string): Promise<any> => {
    const res = await api.get(`/research/${encodeURIComponent(symbol)}`);
    return res.data;
  },

  getFundamentals: async (symbol: string): Promise<CompanyFundamentals> => {
    const res = await api.get<CompanyFundamentals>(`/research/${encodeURIComponent(symbol)}/fundamentals`);
    return res.data;
  },

  getTechnical: async (symbol: string, period: string = '6mo'): Promise<TechnicalAnalysis> => {
    const res = await api.get<TechnicalAnalysis>(`/research/${encodeURIComponent(symbol)}/technical`, {
      params: { period },
    });
    return res.data;
  },

  chat: async (
    message: string,
    sessionId: string = 'default-session',
    symbol?: string,
    includePortfolio: boolean = false
  ): Promise<ResearchChatMessageItem> => {
    const res = await api.post<ResearchChatMessageItem>('/research/chat', {
      message,
      session_id: sessionId,
      symbol,
      include_portfolio: includePortfolio,
    });
    return res.data;
  },

  getChatHistory: async (sessionId: string): Promise<ResearchChatMessageItem[]> => {
    const res = await api.get<ResearchChatMessageItem[]>('/research/chat/history', {
      params: { session_id: sessionId },
    });
    return res.data;
  },

  compare: async (symbols: string[], period: string = '6mo'): Promise<StockComparison> => {
    const res = await api.post<StockComparison>('/research/compare', {
      symbols,
      period,
    });
    return res.data;
  },

  createReport: async (symbol: string, title?: string): Promise<ResearchReportItem> => {
    const res = await api.post<ResearchReportItem>('/research/reports', {
      symbol,
      title,
    });
    return res.data;
  },

  listReports: async (symbol?: string): Promise<ResearchReportItem[]> => {
    const res = await api.get<ResearchReportItem[]>('/research/reports', {
      params: symbol ? { symbol } : undefined,
    });
    return res.data;
  },

  getReport: async (reportId: number): Promise<ResearchReportItem> => {
    const res = await api.get<ResearchReportItem>(`/research/reports/${reportId}`);
    return res.data;
  },
};

export const newsApi = {
  getNews: async (params?: {
    symbol?: string;
    category?: string;
    sentiment_label?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; items: NewsItem[] }> => {
    const res = await api.get('/news', { params });
    return res.data;
  },

  getMarketOverview: async (): Promise<MarketNewsOverview> => {
    const res = await api.get<MarketNewsOverview>('/news/market/overview');
    return res.data;
  },

  getNewsForSymbol: async (symbol: string, limit: number = 15): Promise<{ total: number; items: NewsItem[] }> => {
    const res = await api.get(`/news/symbol/${encodeURIComponent(symbol)}`, {
      params: { limit },
    });
    return res.data;
  },

  getCompanySentiment: async (symbol: string, timeframe: string = '7d'): Promise<CompanySentimentSummary> => {
    const res = await api.get<CompanySentimentSummary>(`/news/sentiment/${encodeURIComponent(symbol)}`, {
      params: { timeframe },
    });
    return res.data;
  },

  getSentimentTrends: async (symbol: string, days: number = 14): Promise<SentimentTimelinePoint[]> => {
    const res = await api.get<SentimentTimelinePoint[]>(`/news/sentiment/trends/${encodeURIComponent(symbol)}`, {
      params: { days },
    });
    return res.data;
  },

  getNewsCorrelation: async (newsId: number): Promise<NewsCorrelation> => {
    const res = await api.get<NewsCorrelation>(`/news/correlation/${newsId}`);
    return res.data;
  },

  getNewsAlerts: async (limit: number = 50): Promise<NewsAlertItem[]> => {
    const res = await api.get<NewsAlertItem[]>('/news/alerts', {
      params: { limit },
    });
    return res.data;
  },

  refreshNews: async (symbols?: string[]): Promise<any> => {
    const res = await api.post('/news/refresh', { symbols });
    return res.data;
  },

  analyzeArticle: async (newsId: number): Promise<NewsItem> => {
    const res = await api.post<NewsItem>(`/news/analyze/${newsId}`);
    return res.data;
  },

  getNewsDetail: async (newsId: number): Promise<NewsItem> => {
    const res = await api.get<NewsItem>(`/news/${newsId}`);
    return res.data;
  },
};

export const authApi = {
  register: async (data: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }): Promise<AuthTokenResponse> => {
    const res = await api.post<AuthTokenResponse>('/auth/register', data);
    return res.data;
  },

  login: async (credentials: {
    username_or_email: string;
    password: string;
  }): Promise<AuthTokenResponse> => {
    const res = await api.post<AuthTokenResponse>('/auth/login', credentials);
    return res.data;
  },

  refresh: async (refreshToken: string): Promise<{ access_token: string; expires_in: number }> => {
    const res = await api.post<{ access_token: string; expires_in: number }>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return res.data;
  },

  getMe: async (): Promise<UserProfile> => {
    const res = await api.get<UserProfile>('/auth/me');
    return res.data;
  },

  logout: async (): Promise<{ status: string; message: string }> => {
    const res = await api.post<{ status: string; message: string }>('/auth/logout');
    return res.data;
  },
};

export default api;
