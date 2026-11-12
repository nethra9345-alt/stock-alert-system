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
  PriceAlert,
  StockPredictionResponse,
  ModelComparisonResponse,
  ModelInfoResponse
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

export default api;
