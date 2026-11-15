import axios from 'axios';
import { Article, MarketOverview, WatchlistData, AISummaryResult } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const fetchArticles = async (params?: { sector?: string; sentiment?: string; search?: string }): Promise<{
  count: number;
  articles: Article[];
  sector: string;
  sector_gainers: any[];
  sector_losers: any[];
}> => {
  const { data } = await apiClient.get('/news/articles', { params });
  return data;
};

export const fetchMarketOverview = async (): Promise<MarketOverview> => {
  const { data } = await apiClient.get('/news/market-overview');
  return data;
};

export const fetchWatchlist = async (userId: string = 'guest_user'): Promise<WatchlistData> => {
  const { data } = await apiClient.get(`/watchlist/${userId}`);
  return data;
};

export const addWatchlistSymbol = async (symbol: string, userId: string = 'guest_user'): Promise<WatchlistData> => {
  const { data } = await apiClient.post('/watchlist/add', { user_id: userId, symbol });
  return data;
};

export const removeWatchlistSymbol = async (symbol: string, userId: string = 'guest_user'): Promise<WatchlistData> => {
  const { data } = await apiClient.delete(`/watchlist/remove/${userId}/${symbol}`);
  return data;
};

export const searchStocks = async (query: string): Promise<Array<{ symbol: string; name: string; sector: string }>> => {
  if (!query || query.trim().length < 1) return [];
  const { data } = await apiClient.get('/stocks/search', { params: { q: query } });
  return data;
};

export const summarizeArticle = async (url: string): Promise<AISummaryResult> => {
  const { data } = await apiClient.get('/ai/summarize', { params: { url } });
  return data;
};

export const fetchSystemLogs = async (): Promise<{ logs: string[] }> => {
  const { data } = await apiClient.get('/system/logs');
  return data;
};

export const registerUser = async (data: { username: string; email: string; password: string }) => {
  const resp = await apiClient.post('/auth/register', data);
  if (resp.data.access_token) {
    localStorage.setItem('finsentiq_token', resp.data.access_token);
    localStorage.setItem('finsentiq_user', JSON.stringify(resp.data.user));
  }
  return resp.data;
};

export const loginUser = async (data: { username_or_email: string; password: string }) => {
  const resp = await apiClient.post('/auth/login', data);
  if (resp.data.access_token) {
    localStorage.setItem('finsentiq_token', resp.data.access_token);
    localStorage.setItem('finsentiq_user', JSON.stringify(resp.data.user));
  }
  return resp.data;
};

export const logoutUser = () => {
  localStorage.removeItem('finsentiq_token');
  localStorage.removeItem('finsentiq_user');
};

export const getStoredUser = () => {
  const u = localStorage.getItem('finsentiq_user');
  return u ? JSON.parse(u) : null;
};
