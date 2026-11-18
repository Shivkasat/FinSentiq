import React from 'react';
import {
  Activity,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Zap,
  BarChart3,
  Sparkles,
  Lock,
  Globe2,
  Cpu,
  Layers,
  ChevronRight,
} from 'lucide-react';

interface LandingPageProps {
  onLaunchDashboard: () => void;
  onOpenAuth: (mode: 'login' | 'register') => void;
  user: any | null;
  totalArticles?: number;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onLaunchDashboard,
  onOpenAuth,
  user,
  totalArticles = 167,
}) => {
  return (
    <div className="min-h-screen bg-[#0B0E14] text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Hero Section */}
      <section className="relative pt-16 pb-16 px-6 overflow-hidden">
        {/* Ambient Gradient Glows */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[350px] bg-indigo-600/15 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-1/3 right-1/4 w-[350px] h-[250px] bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative z-10 space-y-6">
          
          {/* Pill Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface border border-surface-border text-xs font-mono text-slate-300 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Dalal Street Market Intelligence</span>
            <span className="text-slate-600">•</span>
            <span className="text-emerald-400 font-semibold">Live Market Pulse</span>
          </div>

          {/* Main Title */}
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
            Transform Indian Market Noise into{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-emerald-400 bg-clip-text text-transparent">
              High-Conviction Catalysts
            </span>
          </h1>

          {/* Subtitle */}
          <p className="max-w-2xl mx-auto text-sm sm:text-base text-slate-400 leading-relaxed font-normal">
            Real-time news sentiment intelligence monitoring <strong>750+ NSE & BSE equities</strong>. 
            Instant sector matrices, breaking news summaries, and stock catalyst tracking for active market participants.
          </p>

          {/* Hero CTAs */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onLaunchDashboard}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 flex items-center justify-center gap-2.5 transition transform hover:-translate-y-0.5"
            >
              <span>Explore Live Terminal</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => onOpenAuth('register')}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-surface hover:bg-surface-hover border border-surface-border hover:border-slate-600 text-slate-200 font-semibold text-sm transition"
            >
              Create Free Account
            </button>
          </div>

          {/* Institutional Metric Strip */}
          <div className="pt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            <div className="p-4 rounded-xl border border-surface-border bg-surface/50 text-center">
              <span className="block text-2xl font-extrabold font-mono text-white">758+</span>
              <span className="text-xs text-slate-400">NSE/BSE Equities Mapped</span>
            </div>
            <div className="p-4 rounded-xl border border-surface-border bg-surface/50 text-center">
              <span className="block text-2xl font-extrabold font-mono text-emerald-400">&lt; 1 Sec</span>
              <span className="text-xs text-slate-400">Live Signal Speed</span>
            </div>
            <div className="p-4 rounded-xl border border-surface-border bg-surface/50 text-center">
              <span className="block text-2xl font-extrabold font-mono text-indigo-400">10+</span>
              <span className="text-xs text-slate-400">Financial News Feeds</span>
            </div>
            <div className="p-4 rounded-xl border border-surface-border bg-surface/50 text-center">
              <span className="block text-2xl font-extrabold font-mono text-amber-400">24/7</span>
              <span className="text-xs text-slate-400">Automated Market Coverage</span>
            </div>
          </div>

        </div>
      </section>

      {/* Feature Section */}
      <section id="features" className="py-20 px-6 border-t border-surface-border/60 bg-[#0B0E14]/80">
        <div className="max-w-6xl mx-auto space-y-12">
          
          <div className="text-center space-y-2">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400 font-mono">
              Key Platform Advantages
            </h2>
            <h3 className="text-2xl sm:text-3xl font-bold text-white">
              Institutional Market Sentiment Intelligence
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
              Empowering Indian investors and traders with automated sentiment scoring and sector trend analytics.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Card 1 */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-indigo-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <BarChart3 className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Sectoral Sentiment Matrix</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automated multi-sector classification grouping news into Banking, IT, Auto, Pharma, Energy, Metals, FMCG, and Realty with weighted bullish/bearish scores.
              </p>
            </div>

            {/* Card 2 */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-emerald-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <Sparkles className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Deep AI Full-Body Synthesis</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Click any news article to trigger asynchronous web crawling, extracting the full article body and generating executive bullet-point takeaways in seconds.
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-amber-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
                <Zap className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Time Decay & Source Multipliers</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Scores dynamically halve every 6 hours based on publication recency, with premium financial publications (ET, Mint, BS) receiving priority weighting.
              </p>
            </div>

            {/* Card 4: Smart Divergence Radar */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-cyan-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Smart Divergence & Mispricing Radar</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                4-Quadrant algorithmic matrix detecting disconnects between news sentiment and price action — uncovering institutional dip-buys and retail bull traps.
              </p>
            </div>

            {/* Card 5: Portfolio Risk Scanner */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-rose-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center">
                <Lock className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Portfolio Risk & Catalyst Scanner</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Upload your equity portfolio (CSV or quick builder) to cross-reference your capital exposure against live regulatory, earnings, and news downside risks.
              </p>
            </div>

            {/* Card 6: Ask FinSentiq AI Copilot */}
            <div className="p-6 rounded-2xl border border-surface-border bg-surface hover:border-indigo-500/50 transition duration-300 space-y-4">
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Cpu className="h-5 w-5" />
              </div>
              <h4 className="text-base font-bold text-white">Ask FinSentiq AI Market Copilot</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Dalal Street dedicated conversational copilot providing grounded, citation-backed answers on Indian equities directly from verified financial filings.
              </p>
            </div>

          </div>

        </div>
      </section>

      {/* Architecture Section */}
      {/* How it works Section */}
      <section id="architecture" className="py-20 px-6 border-t border-surface-border/60 bg-[#111622]/40">
        <div className="max-w-5xl mx-auto space-y-10">
          
          <div className="text-center space-y-2">
            <h2 className="text-xs font-bold uppercase tracking-widest text-emerald-400 font-mono">
              Simple 3-Step Workflow
            </h2>
            <h3 className="text-2xl sm:text-3xl font-bold text-white">
              How FinSentiq Powers Your Trading Edge
            </h3>
          </div>

          <div className="rounded-2xl border border-surface-border bg-surface p-8 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              <div className="space-y-2">
                <span className="text-xs font-mono font-bold text-indigo-400">01. 24/7 Market Scrape</span>
                <h5 className="text-sm font-bold text-white">Real-Time Ingestion</h5>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Continuously aggregates breaking stories and filings across leading Indian business publications.
                </p>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-mono font-bold text-emerald-400">02. Noise Filtering</span>
                <h5 className="text-sm font-bold text-white">Catalyst Identification</h5>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Detects stock tickers, classifies sentiment direction, and filters out irrelevant noise automatically.
                </p>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-mono font-bold text-sky-400">03. Actionable Insights</span>
                <h5 className="text-sm font-bold text-white">Live Terminal Feeds</h5>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Presents sector heatmaps, top mover catalysts, and executive article briefs on demand.
                </p>
              </div>

            </div>
          </div>

        </div>
      </section>

      {/* Final CTA Strip */}
      <section className="py-16 px-6 border-t border-surface-border bg-gradient-to-b from-[#111622] to-[#0B0E14] text-center">
        <div className="max-w-3xl mx-auto space-y-5">
          <h3 className="text-2xl sm:text-3xl font-extrabold text-white">
            Ready to explore real-time Dalal Street sentiment?
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Open the full interactive terminal now or register for personalized portfolio watchlists.
          </p>
          <div className="pt-2 flex justify-center gap-4">
            <button
              onClick={onLaunchDashboard}
              className="px-8 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 flex items-center gap-2 transition"
            >
              <span>Launch Terminal Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-surface-border bg-surface/50 py-6 px-6 text-center text-xs text-slate-500">
        <p>© 2026 FinSentiq. Indian Stock Market Intelligence & Sentiment Terminal.</p>
      </footer>

    </div>
  );
};
