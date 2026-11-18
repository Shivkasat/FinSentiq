import React from 'react';
import { Activity, Star, Terminal, Sun, Moon, LogIn, LogOut, User as UserIcon, Home, LayoutDashboard, Sparkles, Bot, ShieldAlert, Radar, RefreshCw } from 'lucide-react';

interface NavbarProps {
  currentView: 'landing' | 'dashboard';
  onNavigate: (view: 'landing' | 'dashboard') => void;
  lastUpdated?: string;
  totalArticles?: number;
  overallMood?: string;
  isBackendConnected?: boolean;
  watchlistCount?: number;
  onOpenWatchlist: () => void;
  onOpenPortfolio: () => void;
  onOpenDivergence: () => void;
  onOpenLogs: () => void;
  onOpenCopilot: () => void;
  onOpenAuth: (mode: 'login' | 'register') => void;
  onRefreshFeeds?: () => void;
  isRefreshingFeeds?: boolean;
  user: any | null;
  onLogout: () => void;
  isLightMode: boolean;
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  onNavigate,
  lastUpdated,
  totalArticles = 0,
  overallMood = 'Neutral',
  isBackendConnected = false,
  watchlistCount = 0,
  onOpenWatchlist,
  onOpenPortfolio,
  onOpenDivergence,
  onOpenLogs,
  onOpenCopilot,
  onOpenAuth,
  onRefreshFeeds,
  isRefreshingFeeds = false,
  user,
  onLogout,
  isLightMode,
  onToggleTheme,
}) => {
  return (
    <header className="border-b border-surface-border bg-surface/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand & View Switcher */}
        <div className="flex items-center gap-4">
          <div
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <Activity className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  FinSentiq
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 font-semibold tracking-wider">
                  NSE / BSE
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium hidden sm:block">
                Indian Stock Market Sentiment & Catalyst Engine
              </p>
            </div>
          </div>

          {/* Quick Nav Toggle */}
          <div className="hidden md:flex items-center gap-1 bg-[#0B0E14] p-1 rounded-lg border border-surface-border ml-2 text-xs font-semibold">
            <button
              onClick={() => onNavigate('landing')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                currentView === 'landing' ? 'bg-surface text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Home className="h-3.5 w-3.5" />
              <span>Overview</span>
            </button>
            <button
              onClick={() => onNavigate('dashboard')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                currentView === 'dashboard' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span>Live Terminal</span>
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          
          {/* Live Status Pill */}
          <div className="hidden lg:flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-[#0B0E14] border border-surface-border text-xs font-mono">
            {isBackendConnected && totalArticles > 0 ? (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-slate-200 font-semibold">{totalArticles} Live Articles</span>
                </div>
                <span className="text-slate-600">•</span>
                <span className="text-slate-400">10m Auto-Sweep</span>
                <span className="text-slate-600">•</span>
                <span className={overallMood === 'Bullish' ? 'text-emerald-400 font-bold' : overallMood === 'Bearish' ? 'text-rose-400 font-bold' : 'text-slate-400'}>
                  {overallMood}
                </span>

                {onRefreshFeeds && (
                  <button
                    onClick={onRefreshFeeds}
                    disabled={isRefreshingFeeds}
                    className="ml-1 px-2.5 py-1 rounded bg-surface border border-surface-border hover:border-indigo-500/50 hover:bg-indigo-500/10 text-slate-200 flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
                    title="Fetch fresh live RSS feeds from financial publications right now"
                  >
                    <RefreshCw className={`h-3 w-3 ${isRefreshingFeeds ? 'animate-spin text-indigo-400' : 'text-slate-400'}`} />
                    <span className="text-[11px] font-sans font-medium text-slate-300">
                      {isRefreshingFeeds ? 'Refreshing...' : 'Sync Live'}
                    </span>
                  </button>
                )}
              </>
            ) : (
              <div className="flex items-center gap-2 text-rose-400">
                <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
                <span>Backend Offline (Port 8000)</span>
              </div>
            )}
          </div>

          {/* AI Copilot Button */}
          <button
            onClick={onOpenCopilot}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/40 hover:bg-indigo-600/30 text-xs font-semibold text-indigo-300 transition shadow-sm shadow-indigo-500/10"
            title="Ask Market Copilot"
          >
            <Bot className="h-4 w-4 text-indigo-400" />
            <span className="hidden sm:inline">Ask Copilot</span>
            <span className="px-1 py-0.2 rounded bg-indigo-500/30 text-[9px] font-mono text-indigo-200">AI</span>
          </button>

          {/* Divergence Radar Button */}
          <button
            onClick={onOpenDivergence}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500/10 via-cyan-500/10 to-indigo-500/10 border border-cyan-500/30 hover:border-cyan-400 hover:bg-cyan-500/20 text-xs font-semibold text-cyan-300 transition shadow-sm"
            title="Open Smart Divergence & Mispricing Radar"
          >
            <Radar className="h-4 w-4 text-cyan-400" />
            <span className="hidden sm:inline">Divergence Radar</span>
            <span className="px-1 py-0.2 rounded bg-cyan-500/30 text-[9px] font-mono text-cyan-200">RADAR</span>
          </button>

          {/* Portfolio Scanner Button */}
          <button
            onClick={onOpenPortfolio}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-surface-border hover:border-indigo-500/50 hover:bg-indigo-500/10 text-xs font-semibold text-slate-200 transition"
            title="Scan your stock portfolio against news risk"
          >
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <span className="hidden sm:inline">Portfolio Risk</span>
          </button>

          {/* Watchlist Button */}
          <button
            onClick={onOpenWatchlist}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-surface-border hover:border-amber-500/50 hover:bg-amber-500/10 text-xs font-semibold text-slate-200 transition"
          >
            <Star className="h-4 w-4 text-amber-400 fill-current" />
            <span className="hidden sm:inline">Watchlist</span>
            <span className="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-400 font-mono text-[10px]">
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

          {/* Auth User Info / Login Button */}
          {user ? (
            <div className="flex items-center gap-2 pl-1 border-l border-surface-border">
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0B0E14] border border-surface-border text-xs font-semibold text-indigo-300">
                <UserIcon className="h-3.5 w-3.5 text-indigo-400" />
                <span className="max-w-[90px] truncate">{user.username}</span>
              </div>
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 pl-1 border-l border-surface-border">
              <button
                onClick={() => onOpenAuth('login')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Sign In</span>
              </button>
            </div>
          )}

        </div>

      </div>
    </header>
  );
};
