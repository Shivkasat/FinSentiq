import React from 'react';
import { TrendingUp, TrendingDown, Star } from 'lucide-react';
import { StockMover } from '../types';

interface MoversProps {
  gainers: StockMover[];
  losers: StockMover[];
  watchlist: string[];
  onToggleWatchlist: (symbol: string) => void;
  selectedSector: string;
}

export const MarketMovers: React.FC<MoversProps> = ({
  gainers,
  losers,
  watchlist,
  onToggleWatchlist,
  selectedSector,
}) => {
  const isOverall = !selectedSector || selectedSector === 'All';
  const sectorTitle = isOverall ? 'Overall Market' : selectedSector;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
          Catalyst Movers — <span className="text-indigo-400">{sectorTitle}</span>
        </span>
        <span className="text-[11px] text-slate-400 font-mono">
          {isOverall ? 'Top market movers' : `Filtered by ${selectedSector}`}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Bullish Catalysts (Positive) */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Bullish Catalysts (Positive)
              </h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
              {gainers.length} Found
            </span>
          </div>

          <div className="space-y-2">
            {gainers.slice(0, 5).map((stock) => (
              <div
                key={stock.symbol}
                className="flex items-center justify-between p-2.5 rounded-lg bg-[#0B0E14]/50 border border-surface-border/60 hover:border-slate-700 transition"
              >
                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => onToggleWatchlist(stock.symbol)}
                    className={`p-1 rounded transition ${
                      watchlist.includes(stock.symbol) ? 'text-amber-400' : 'text-slate-500 hover:text-white'
                    }`}
                    title={watchlist.includes(stock.symbol) ? 'In Watchlist' : 'Add to Watchlist'}
                  >
                    <Star className="h-3.5 w-3.5 fill-current" />
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-white">{stock.symbol}</span>
                      {stock.price && (
                        <span className="text-[11px] font-mono text-slate-300">
                          ₹{stock.price.toLocaleString('en-IN')}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-400 line-clamp-1">{stock.sector}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {stock.percent_change !== undefined && (
                    <div className="text-right">
                      <span className={`text-[11px] font-mono font-bold ${stock.percent_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {stock.percent_change >= 0 ? `+${stock.percent_change}%` : `${stock.percent_change}%`}
                      </span>
                      {stock.prediction_aligned && (
                        <span className="block text-[9px] uppercase tracking-wider text-emerald-400/90 font-medium">
                          ✓ Aligned
                        </span>
                      )}
                    </div>
                  )}
                  <div className="text-right border-l border-slate-800 pl-2.5">
                    <span className="font-mono text-xs font-bold text-emerald-400">+{stock.net_score}</span>
                    <p className="text-[10px] text-slate-400 font-mono">{stock.article_count} news</p>
                  </div>
                </div>
              </div>
            ))}
            {gainers.length === 0 && (
              <div className="py-6 text-center text-xs text-slate-400 bg-[#0B0E14]/30 rounded-lg border border-surface-border/40">
                No active positive catalysts in {sectorTitle}
              </div>
            )}
          </div>
        </div>

        {/* Bearish Headwinds (Negative) */}
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-rose-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Bearish Headwinds (Negative)
              </h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 font-bold border border-rose-500/20">
              {losers.length} Found
            </span>
          </div>

          <div className="space-y-2">
            {losers.slice(0, 5).map((stock) => (
              <div
                key={stock.symbol}
                className="flex items-center justify-between p-2.5 rounded-lg bg-[#0B0E14]/50 border border-surface-border/60 hover:border-slate-700 transition"
              >
                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => onToggleWatchlist(stock.symbol)}
                    className={`p-1 rounded transition ${
                      watchlist.includes(stock.symbol) ? 'text-amber-400' : 'text-slate-500 hover:text-white'
                    }`}
                    title={watchlist.includes(stock.symbol) ? 'In Watchlist' : 'Add to Watchlist'}
                  >
                    <Star className="h-3.5 w-3.5 fill-current" />
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-white">{stock.symbol}</span>
                      {stock.price && (
                        <span className="text-[11px] font-mono text-slate-300">
                          ₹{stock.price.toLocaleString('en-IN')}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-400 line-clamp-1">{stock.sector}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {stock.percent_change !== undefined && (
                    <div className="text-right">
                      <span className={`text-[11px] font-mono font-bold ${stock.percent_change <= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {stock.percent_change > 0 ? `+${stock.percent_change}%` : `${stock.percent_change}%`}
                      </span>
                      {stock.prediction_aligned && (
                        <span className="block text-[9px] uppercase tracking-wider text-rose-400/90 font-medium">
                          ✓ Aligned
                        </span>
                      )}
                    </div>
                  )}
                  <div className="text-right border-l border-slate-800 pl-2.5">
                    <span className="font-mono text-xs font-bold text-rose-400">{stock.net_score}</span>
                    <p className="text-[10px] text-slate-400 font-mono">{stock.article_count} news</p>
                  </div>
                </div>
              </div>
            ))}
            {losers.length === 0 && (
              <div className="py-6 text-center text-xs text-slate-400 bg-[#0B0E14]/30 rounded-lg border border-surface-border/40">
                No active negative headwinds in {sectorTitle}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
