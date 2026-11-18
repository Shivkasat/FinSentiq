import React from 'react';
import { Zap, ArrowUpRight, ArrowDownRight, Minus, Sparkles } from 'lucide-react';
import { Article } from '../types';

interface TickerProps {
  articles: Article[];
  onOpenSummary: (url: string, title: string) => void;
}

export const BreakingNewsTicker: React.FC<TickerProps> = ({ articles, onOpenSummary }) => {
  // Filter for high impact articles (sentiment magnitude >= 2.0 or specific catalyst)
  const highImpact = articles.filter(
    (a) => Math.abs(a.sentiment_score) >= 2.0 || a.impact_type !== 'Market Catalyst'
  ).slice(0, 10);

  if (highImpact.length === 0) return null;

  return (
    <div className="w-full bg-gradient-to-r from-indigo-950/60 via-[#0B0E14] to-indigo-950/60 border-y border-surface-border py-2 overflow-hidden flex items-center">
      {/* Fixed Tag */}
      <div className="shrink-0 flex items-center gap-1.5 px-3 py-0.5 ml-4 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] font-bold uppercase tracking-wider z-10 shadow-sm">
        <Zap className="h-3 w-3 animate-pulse text-amber-400 fill-current" />
        <span>Breaking Catalysts</span>
      </div>

      {/* Scrolling / Marquee Items */}
      <div className="flex items-center gap-6 overflow-x-auto no-scrollbar whitespace-nowrap pl-4 pr-6 text-xs">
        {highImpact.map((item) => {
          const isBull = item.sentiment_score > 0;
          return (
            <div key={item.id} className="flex items-center gap-2 shrink-0">
              {item.stock_mentions.length > 0 && (
                <span className="font-mono font-bold text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                  {item.stock_mentions[0]}
                </span>
              )}

              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-300 hover:text-white transition line-clamp-1 max-w-[280px] sm:max-w-md truncate"
                title={item.title}
              >
                {item.title}
              </a>

              <span className={`flex items-center gap-0.5 text-[10px] font-mono font-bold ${isBull ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isBull ? <ArrowUpRight className="h-2.5 w-2.5" /> : <ArrowDownRight className="h-2.5 w-2.5" />}
                {isBull ? `+${item.sentiment_score}` : item.sentiment_score}
              </span>

              <button
                onClick={() => onOpenSummary(item.link, item.title)}
                className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold px-1 rounded bg-indigo-500/10 transition"
              >
                AI Brief
              </button>

              <span className="text-slate-700 mx-1">•</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
