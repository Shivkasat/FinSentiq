import axios from 'axios';
import { Article, MarketOverview } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const fetchArticles = async (params?: { sector?: string; sentiment?: string; search?: string }): Promise<{ count: number; articles: Article[] }> => {
  const { data } = await apiClient.get('/news/articles', { params });
  return data;
};

export const fetchMarketOverview = async (): Promise<MarketOverview> => {
  const { data } = await apiClient.get('/news/market-overview');
  return data;
};

export const fetchWatchlist = async (userId: string = 'guest_user'): Promise<{ user_id: string; symbols: string[] }> => {
  const { data } = await apiClient.get(`/watchlist/${userId}`);
  return data;
};

export const addWatchlistSymbol = async (symbol: string, userId: string = 'guest_user'): Promise<{ symbols: string[] }> => {
  const { data } = await apiClient.post('/watchlist/add', { user_id: userId, symbol });
  return data;
};

export const removeWatchlistSymbol = async (symbol: string, userId: string = 'guest_user'): Promise<{ symbols: string[] }> => {
  const { data } = await apiClient.delete(`/watchlist/remove/${userId}/${symbol}`);
  return data;
};
