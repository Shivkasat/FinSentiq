import React, { useState } from 'react';
import { Search, Star, Trash2, TrendingUp, TrendingDown, Plus, ShieldCheck } from 'lucide-react';
import { WatchlistData } from '../types';
import { searchStocks } from '../api';

interface WatchlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  watchlistData: WatchlistData | undefined;
  onAddSymbol: (symbol: string) => void;
  onRemoveSymbol: (symbol: string) => void;
}

export const WatchlistModal: React.FC<WatchlistModalProps> = ({
  isOpen,
  onClose,
  watchlistData,
  onAddSymbol,
  onRemoveSymbol,
}) => {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ symbol: string; name: string; sector: string }>>([]);
  const [searching, setSearching] = useState(false);

  if (!isOpen) return null;

  const handleSearchChange = async (val: string) => {
    setQuery(val);
    if (val.trim().length >= 2) {
      setSearching(true);
      try {
        const res = await searchStocks(val);
        setSearchResults(res);
      } catch (e) {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    } else {
      setSearchResults([]);
    }
  };

  const handleAdd = (sym: string) => {
    onAddSymbol(sym);
    setQuery('');
    setSearchResults([]);
  };

  const stocks = watchlistData?.stocks || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl rounded-2xl border border-surface-border bg-[#111622] p-6 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-surface-border/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Star className="h-5 w-5 fill-current" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Personal Portfolio Watchlist
              </h3>
              <p className="text-xs text-slate-400 font-mono">Real-time Stock Monitor & Tracking</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition"
          >
            Done
          </button>
        </div>

        {/* Autocomplete Search input */}
        <div className="py-4 relative">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search 750+ Indian Equities (e.g. Reliance, HDFC, Tata, Infy)..."
              value={query}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-[#0B0E14] border border-surface-border text-sm text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute top-16 left-0 right-0 z-20 rounded-xl border border-surface-border bg-surface shadow-2xl max-h-60 overflow-y-auto p-1.5 space-y-1">
              {searchResults.map((item) => (
                <div
                  key={item.symbol}
                  onClick={() => handleAdd(item.symbol)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover cursor-pointer transition text-xs"
                >
                  <div>
                    <span className="font-mono font-bold text-white mr-2">{item.symbol}</span>
                    <span className="text-slate-400">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 font-mono">{item.sector}</span>
                    <Plus className="h-3.5 w-3.5 text-indigo-400" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Watchlist Table */}
        <div className="flex-1 overflow-y-auto pr-1">
          {stocks.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Star className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-sm font-medium">Your watchlist is empty.</p>
              <p className="text-xs text-slate-400">Search above or click the star on any gainer/loser stock card.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {stocks.map((stock) => {
                const isGain = stock.change >= 0;
                return (
                  <div
                    key={stock.symbol}
                    className="flex items-center justify-between p-3 rounded-xl bg-[#0B0E14]/60 border border-surface-border hover:border-slate-700 transition"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg bg-surface flex items-center justify-center font-mono font-bold text-xs text-white border border-surface-border">
                        {stock.symbol.slice(0, 3)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sm text-white">{stock.symbol}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                            {stock.sector}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 font-mono">
                          NSE Reference: ₹{stock.price}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className={`flex items-center justify-end gap-1 font-mono font-bold text-xs ${
                          isGain ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          {isGain ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                          {stock.change > 0 ? `+${stock.change}` : stock.change} ({stock.percent_change}%)
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">Live Session</span>
                      </div>

                      <button
                        onClick={() => onRemoveSymbol(stock.symbol)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
