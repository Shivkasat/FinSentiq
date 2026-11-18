import React from 'react';
import { Target, TrendingUp, CheckCircle, Award } from 'lucide-react';
import { AccuracyScoreboard as AccuracyType } from '../types';

interface AccuracyProps {
  scoreboard?: AccuracyType;
}

export const AccuracyScoreboard: React.FC<AccuracyProps> = ({ scoreboard }) => {
  if (!scoreboard) return null;

  return (
    <div className="rounded-xl border border-surface-border bg-gradient-to-r from-surface via-[#121824] to-surface p-4">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Left: Win Rate & Title */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Target className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Empirical Signal Verification
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Auto-Validated
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Live algorithmic matching of news sentiment signals vs. realized NSE price movements
            </p>
          </div>
        </div>

        {/* Right: Metrics Grid */}
        <div className="flex items-center gap-4 flex-wrap">
          {/* Win Rate */}
          <div className="flex items-center gap-2 bg-[#0B0E14]/70 px-3 py-1.5 rounded-lg border border-surface-border">
            <Award className="h-4 w-4 text-emerald-400" />
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-400">Win Rate</span>
              <span className="font-mono text-sm font-bold text-emerald-400">
                {scoreboard.win_rate}%
              </span>
            </div>
          </div>

          {/* Alpha Spread */}
          <div className="flex items-center gap-2 bg-[#0B0E14]/70 px-3 py-1.5 rounded-lg border border-surface-border">
            <TrendingUp className="h-4 w-4 text-indigo-400" />
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-400">Alpha Spread</span>
              <span className={`font-mono text-sm font-bold ${scoreboard.alpha_spread >= 0 ? 'text-indigo-400' : 'text-slate-400'}`}>
                {scoreboard.alpha_spread > 0 ? `+${scoreboard.alpha_spread}%` : `${scoreboard.alpha_spread}%`}
              </span>
            </div>
          </div>

          {/* Successful / Evaluated */}
          <div className="flex items-center gap-2 bg-[#0B0E14]/70 px-3 py-1.5 rounded-lg border border-surface-border">
            <CheckCircle className="h-4 w-4 text-cyan-400" />
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-400">Hits / Evaluated</span>
              <span className="font-mono text-sm font-bold text-cyan-400">
                {scoreboard.successful_predictions} / {scoreboard.total_signals}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
