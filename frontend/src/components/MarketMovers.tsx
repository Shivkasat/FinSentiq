import React from 'react';
import { TrendingUp, TrendingDown, Star } from 'lucide-react';
import { StockMover } from '../types';

interface MoversProps {
  gainers: StockMover[];
  losers: StockMover[];
  watchlist: string[];
  onToggleWatchlist: (symbol: string) => void;
}

export const MarketMovers: React.FC<MoversProps> = ({ gainers, losers, watchlist, onToggleWatchlist }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      
      {/* Bullish Catalysts */}
      <div className="rounded-xl border border-surface-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-4 w-4 text-emerald-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Top Bullish Catalysts (Gainers)
          </h3>
        </div>
        <div className="space-y-2">
          {gainers.slice(0, 5).map((stock) => (
            <div key={stock.symbol} className="flex items-center justify-between p-2 rounded-lg bg-[#0B0E14]/40 border border-surface-border/50 hover:border-slate-700 transition">
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => onToggleWatchlist(stock.symbol)}
                  className={`p-1 rounded transition ${
                    watchlist.includes(stock.symbol) ? 'text-amber-400' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Star className="h-3.5 w-3.5 fill-current" />
                </button>
                <div>
                  <span className="font-mono font-bold text-xs text-white">{stock.symbol}</span>
                  <p className="text-[10px] text-slate-400 line-clamp-1">{stock.sector}</p>
                </div>
              </div>
              <div className="text-right">
                <span className="font-mono text-xs font-bold text-emerald-400">+{stock.net_score}</span>
                <p className="text-[10px] text-slate-400 font-mono">{stock.article_count} news</p>
              </div>
            </div>
          ))}
          {gainers.length === 0 && <p className="text-xs text-slate-400 py-3 text-center">No active bullish catalysts</p>}
        </div>
      </div>

      {/* Bearish Headwinds */}
      <div className="rounded-xl border border-surface-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingDown className="h-4 w-4 text-rose-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Top Bearish Headwinds (Losers)
          </h3>
        </div>
        <div className="space-y-2">
          {losers.slice(0, 5).map((stock) => (
            <div key={stock.symbol} className="flex items-center justify-between p-2 rounded-lg bg-[#0B0E14]/40 border border-surface-border/50 hover:border-slate-700 transition">
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => onToggleWatchlist(stock.symbol)}
                  className={`p-1 rounded transition ${
                    watchlist.includes(stock.symbol) ? 'text-amber-400' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Star className="h-3.5 w-3.5 fill-current" />
                </button>
                <div>
                  <span className="font-mono font-bold text-xs text-white">{stock.symbol}</span>
                  <p className="text-[10px] text-slate-400 line-clamp-1">{stock.sector}</p>
                </div>
              </div>
              <div className="text-right">
                <span className="font-mono text-xs font-bold text-rose-400">{stock.net_score}</span>
                <p className="text-[10px] text-slate-400 font-mono">{stock.article_count} news</p>
              </div>
            </div>
          ))}
          {losers.length === 0 && <p className="text-xs text-slate-400 py-3 text-center">No active bearish headwinds</p>}
        </div>
      </div>

    </div>
  );
};
