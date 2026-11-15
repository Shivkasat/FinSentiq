import React from 'react';
import { Activity, Star, Terminal, RefreshCw, BarChart3, Sun, Moon } from 'lucide-react';

interface NavbarProps {
  lastUpdated?: string;
  totalArticles?: number;
  overallMood?: string;
  watchlistCount?: number;
  onOpenWatchlist: () => void;
  onOpenLogs: () => void;
  isLightMode: boolean;
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  lastUpdated,
  totalArticles = 0,
  overallMood = 'Neutral',
  watchlistCount = 0,
  onOpenWatchlist,
  onOpenLogs,
  isLightMode,
  onToggleTheme,
}) => {
  return (
    <header className="border-b border-surface-border bg-surface/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                FinSentiq
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 font-semibold tracking-wider">
                v3.0 Cloud
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium hidden sm:block">
              Institutional Stock Market Intelligence & Sentiment Engine
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          
          {/* Live Status Pill */}
          <div className="hidden lg:flex items-center gap-3 px-3.5 py-1.5 rounded-lg bg-[#0B0E14] border border-surface-border text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300 font-semibold">Store Synced</span>
            </div>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">{totalArticles} Articles Active</span>
            <span className="text-slate-600">•</span>
            <span className={overallMood === 'Bullish' ? 'text-emerald-400 font-bold' : overallMood === 'Bearish' ? 'text-rose-400 font-bold' : 'text-slate-400'}>
              Mood: {overallMood}
            </span>
          </div>

          {/* Watchlist Button */}
          <button
            onClick={onOpenWatchlist}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-surface-border hover:border-amber-500/50 hover:bg-amber-500/10 text-xs font-semibold text-slate-200 transition"
          >
            <Star className="h-4 w-4 text-amber-400 fill-current" />
            <span>Watchlist</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-400 font-mono text-[10px]">
              {watchlistCount}
            </span>
          </button>

          {/* Logs Button */}
          <button
            onClick={onOpenLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-surface-border hover:border-slate-600 text-xs font-semibold text-slate-300 transition"
            title="View Engine Logs"
          >
            <Terminal className="h-4 w-4 text-emerald-400" />
            <span className="hidden sm:inline">Logs</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg bg-surface border border-surface-border text-slate-400 hover:text-white transition"
            title="Toggle Theme"
          >
            {isLightMode ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>

        </div>

      </div>
    </header>
  );
};
