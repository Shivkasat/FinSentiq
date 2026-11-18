import React from 'react';
import { ExternalLink, Clock, ArrowUpRight, ArrowDownRight, Minus, Sparkles } from 'lucide-react';
import { Article } from '../types';

interface ArticleCardProps {
  article: Article;
  onOpenSummary: (url: string, title: string) => void;
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article, onOpenSummary }) => {
  const isPositive = article.sentiment_score > 1.5;
  const isNegative = article.sentiment_score < -1.5;

  return (
    <div className="group relative rounded-xl border border-surface-border bg-surface p-5 hover:bg-surface-hover hover:border-slate-700 transition duration-200 flex flex-col justify-between">
      
      {/* Header tags */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {article.sector}
            </span>
            {article.impact_type && article.impact_type !== 'Unknown' && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                article.impact_type.includes('Earnings')
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                  : article.impact_type.includes('Regulatory')
                    ? 'bg-purple-500/10 text-purple-300 border-purple-500/20'
                    : article.impact_type.includes('Orders')
                      ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20'
                      : article.impact_type.includes('Corporate')
                        ? 'bg-blue-500/10 text-blue-300 border-blue-500/20'
                        : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20'
              }`}>
                {article.impact_type}
              </span>
            )}
            <span className="text-xs text-slate-400 font-medium">
              {article.source}
            </span>
          </div>

          {/* Sentiment Badge */}
          <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-bold ${
            isPositive 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
              : isNegative 
                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' 
                : 'bg-slate-700/30 text-slate-400 border border-slate-700'
          }`}>
            {isPositive && <ArrowUpRight className="h-3 w-3" />}
            {isNegative && <ArrowDownRight className="h-3 w-3" />}
            {!isPositive && !isNegative && <Minus className="h-3 w-3" />}
            <span>{article.sentiment_score > 0 ? `+${article.sentiment_score}` : article.sentiment_score}</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-slate-100 group-hover:text-indigo-400 transition leading-snug line-clamp-2 mb-2">
          <a href={article.link} target="_blank" rel="noopener noreferrer" className="flex items-start gap-1">
            <span>{article.title}</span>
            <ExternalLink className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-1" />
          </a>
        </h3>

        {/* Summary Snippet */}
        {article.summary && (
          <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-4">
            {article.summary}
          </p>
        )}
      </div>

      {/* Footer Info */}
      <div className="pt-3 border-t border-surface-border/50 flex items-center justify-between text-xs text-slate-400">
        {/* Stock mentions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {article.stock_mentions.length > 0 ? (
            article.stock_mentions.map((sym) => (
              <span key={sym} className="font-mono font-bold text-[11px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                {sym}
              </span>
            ))
          ) : (
            <span className="text-[11px] text-slate-400 italic">Broad Catalyst</span>
          )}
        </div>

        {/* Actions & Time */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenSummary(article.link, article.title)}
            className="flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-white px-2 py-0.5 rounded bg-indigo-500/10 hover:bg-indigo-600 transition"
          >
            <Sparkles className="h-3 w-3" />
            AI Brief
          </button>
          <span className="flex items-center gap-1 font-mono text-[11px] text-slate-400">
            <Clock className="h-3 w-3" />
            {Math.round(article.age_hours)}h
          </span>
        </div>
      </div>

    </div>
  );
};
