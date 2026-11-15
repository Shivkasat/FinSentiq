import React from 'react';
import { SectorSummary } from '../types';

interface SectorHeatmapProps {
  sectors: SectorSummary[];
  selectedSector: string;
  onSelectSector: (sector: string) => void;
}

export const SectorHeatmap: React.FC<SectorHeatmapProps> = ({ sectors, selectedSector, onSelectSector }) => {
  return (
    <div className="rounded-xl border border-surface-border bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Sectoral Sentiment Matrix
          </h2>
          <p className="text-xs text-slate-400">Real-time aggregate score across NSE/BSE sectors</p>
        </div>
        <button
          onClick={() => onSelectSector('All')}
          className={`text-xs px-2.5 py-1 rounded font-medium transition ${
            selectedSector === 'All'
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          View All Sectors
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {sectors.map((sec) => {
          const isSelected = selectedSector.toLowerCase() === sec.sector.toLowerCase();
          const isBull = sec.avg_sentiment > 0.5;
          const isBear = sec.avg_sentiment < -0.5;

          return (
            <button
              key={sec.sector}
              onClick={() => onSelectSector(sec.sector)}
              className={`rounded-lg p-3 text-left border transition-all duration-200 flex flex-col justify-between ${
                isSelected
                  ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/10'
                  : 'border-surface-border bg-[#0B0E14]/60 hover:bg-surface-hover hover:border-slate-700'
              }`}
            >
              <div>
                <span className="text-xs font-semibold text-slate-200 line-clamp-1">
                  {sec.sector}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {sec.article_count} articles
                </span>
              </div>

              <div className="mt-3 flex items-baseline justify-between">
                <span className={`text-xs font-mono font-bold ${
                  isBull ? 'text-emerald-400' : isBear ? 'text-rose-400' : 'text-slate-400'
                }`}>
                  {sec.avg_sentiment > 0 ? `+${sec.avg_sentiment}` : sec.avg_sentiment}
                </span>
                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                  isBull ? 'bg-emerald-500/10 text-emerald-400' : isBear ? 'bg-rose-500/10 text-rose-400' : 'bg-slate-700/20 text-slate-400'
                }`}>
                  {sec.sentiment_label}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
