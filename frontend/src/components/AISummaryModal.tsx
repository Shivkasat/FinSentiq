import React from 'react';
import { X, Sparkles, ExternalLink, ArrowUpRight, ArrowDownRight, Tag, BookOpen } from 'lucide-react';
import { AISummaryResult } from '../types';

interface SummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  loading: boolean;
  data: AISummaryResult | null;
  targetUrl: string;
}

export const AISummaryModal: React.FC<SummaryModalProps> = ({ isOpen, onClose, loading, data, targetUrl }) => {
  if (!isOpen) return null;

  const isBull = data && data.sentiment_score > 1.5;
  const isBear = data && data.sentiment_score < -1.5;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-2xl border border-surface-border bg-[#111622] p-6 shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-surface-border/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Executive AI Intelligence Briefing
              </h3>
              <p className="text-xs text-slate-400 font-mono">Deep NLP Full-Text Synthesis</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="py-5 space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="h-8 w-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
              <p className="text-xs text-slate-300 font-medium">Extracting article content & computing multi-layer catalysts...</p>
            </div>
          ) : data ? (
            <>
              {/* Badges Bar */}
              <div className="flex flex-wrap items-center gap-2">
                <span className={`flex items-center gap-1 text-xs font-mono font-bold px-2.5 py-1 rounded-md ${
                  isBull ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  isBear ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                  'bg-slate-700/20 text-slate-400 border border-slate-700'
                }`}>
                  {isBull && <ArrowUpRight className="h-3.5 w-3.5" />}
                  {isBear && <ArrowDownRight className="h-3.5 w-3.5" />}
                  Sentiment: {data.sentiment} ({data.sentiment_score > 0 ? `+${data.sentiment_score}` : data.sentiment_score})
                </span>

                <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                  Sector: {data.sector}
                </span>

                {data.impact_type && (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    Impact: {data.impact_type}
                  </span>
                )}
              </div>

              {/* Title */}
              <h4 className="text-base font-semibold text-slate-100 leading-snug">
                {data.title}
              </h4>

              {/* Summary Body */}
              <div className="p-4 rounded-xl bg-[#0B0E14] border border-surface-border text-sm text-slate-200 leading-relaxed space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
                  <BookOpen className="h-3.5 w-3.5" />
                  Key Article Takeaways
                </div>
                <p>{data.summary}</p>
              </div>

              {/* Mentioned Symbols */}
              {data.stock_mentions && data.stock_mentions.length > 0 && (
                <div>
                  <span className="text-xs text-slate-400 block mb-1.5 font-medium">Mapped Equities:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {data.stock_mentions.map((sym) => (
                      <span key={sym} className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                        {sym}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Link */}
              <div className="pt-2 flex justify-between items-center text-xs text-slate-400 border-t border-surface-border/40">
                <span>Body Word Count: {data.word_count} words</span>
                <a
                  href={targetUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  View Full Article Source <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </>
          ) : (
            <p className="text-center py-8 text-sm text-slate-400">Could not extract summary for this article.</p>
          )}
        </div>

      </div>
    </div>
  );
};
