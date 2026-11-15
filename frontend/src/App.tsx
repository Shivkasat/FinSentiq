import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { SectorHeatmap } from './components/SectorHeatmap';
import { MarketMovers } from './components/MarketMovers';
import { ArticleCard } from './components/ArticleCard';
import { fetchArticles, fetchMarketOverview, fetchWatchlist, addWatchlistSymbol, removeWatchlistSymbol } from './api';
import { Search, Filter, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';

export const App: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedSector, setSelectedSector] = useState<string>('All');
  const [selectedSentiment, setSelectedSentiment] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // 1. Fetch Market Overview (Cached automatically via TanStack Query)
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['market-overview'],
    queryFn: fetchMarketOverview,
    refetchInterval: 60 * 1000, // Background poll every 60s
    staleTime: 30 * 1000,
  });

  // 2. Fetch Articles (Instant load from memory store)
  const { data: articlesData, isLoading: articlesLoading } = useQuery({
    queryKey: ['articles', selectedSector, selectedSentiment, searchQuery],
    queryFn: () => fetchArticles({
      sector: selectedSector !== 'All' ? selectedSector : undefined,
      sentiment: selectedSentiment || undefined,
      search: searchQuery || undefined,
    }),
    staleTime: 15 * 1000,
  });

  // 3. User Watchlist
  const { data: watchlistData } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => fetchWatchlist('guest_user'),
  });

  const watchlist = watchlistData?.symbols || [];

  const toggleWatchlistMutation = useMutation({
    mutationFn: async (symbol: string) => {
      if (watchlist.includes(symbol)) {
        return removeWatchlistSymbol(symbol, 'guest_user');
      } else {
        return addWatchlistSymbol(symbol, 'guest_user');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });

  const handleToggleWatchlist = (symbol: string) => {
    toggleWatchlistMutation.mutate(symbol);
  };

  return (
    <div className="min-h-screen bg-[#0B0E14] text-slate-100 flex flex-col font-sans">
      
      {/* Top Navigation */}
      <Navbar
        lastUpdated={overview?.last_updated}
        totalArticles={overview?.summary?.total_articles}
        overallMood={overview?.summary?.overall_mood}
      />

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 space-y-6">
        
        {/* Sector Heatmap */}
        {overview?.summary?.sectors && (
          <SectorHeatmap
            sectors={overview.summary.sectors}
            selectedSector={selectedSector}
            onSelectSector={setSelectedSector}
          />
        )}

        {/* Top Movers (Bullish vs Bearish) */}
        {overview && (
          <MarketMovers
            gainers={overview.gainers || []}
            losers={overview.losers || []}
            watchlist={watchlist}
            onToggleWatchlist={handleToggleWatchlist}
          />
        )}

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl border border-surface-border bg-surface">
          
          {/* Search */}
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search symbol (e.g. RELIANCE, TCS) or headline..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#0B0E14] border border-surface-border text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>

          {/* Sentiment Filter Tabs */}
          <div className="flex items-center gap-1.5 w-full sm:w-auto">
            {['', 'Positive', 'Neutral', 'Negative'].map((sent) => (
              <button
                key={sent}
                onClick={() => setSelectedSentiment(sent)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
                  selectedSentiment === sent
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'bg-[#0B0E14] text-slate-400 hover:text-white border border-surface-border'
                }`}
              >
                {sent === '' ? 'All Sentiment' : sent}
              </button>
            ))}
          </div>

        </div>

        {/* Active Filter Header */}
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing <strong className="text-white">{articlesData?.count || 0}</strong> intelligence articles for sector: <span className="text-indigo-400 font-semibold">{selectedSector}</span>
          </span>
          <span className="font-mono text-[11px] text-slate-400">
            Store State: Active (Zero User Feed Reload)
          </span>
        </div>

        {/* Articles Grid */}
        {articlesLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div key={n} className="h-44 rounded-xl border border-surface-border bg-surface animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {articlesData?.articles?.map((art) => (
              <ArticleCard key={art.id || art.link} article={art} />
            ))}
            {articlesData?.articles?.length === 0 && (
              <div className="col-span-full py-16 text-center text-slate-400">
                <ShieldAlert className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                <p className="text-sm font-medium">No articles found matching the current criteria.</p>
              </div>
            )}
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border bg-surface/50 py-4 px-6 mt-12 text-center text-xs text-slate-400">
        <p>FinSentiq v3.0 Cloud Platform • High-Concurrency Async Architecture • NSE/BSE Equity Intelligence</p>
      </footer>

    </div>
  );
};
