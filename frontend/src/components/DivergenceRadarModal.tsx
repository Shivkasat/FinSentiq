import React, { useState, useEffect } from 'react';
import { 
  X, Radar, TrendingUp, TrendingDown, AlertTriangle, 
  ArrowUpRight, ArrowDownRight, Compass, ShieldAlert,
  ExternalLink, Sparkles, RefreshCw, Zap
} from 'lucide-react';
import { DivergenceRadarResponse, DivergenceAnomaly } from '../types';
import { fetchDivergenceRadar } from '../api';

interface DivergenceRadarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenCopilot?: (symbol: string) => void;
}

export const DivergenceRadarModal: React.FC<DivergenceRadarModalProps> = ({
  isOpen,
  onClose,
  onOpenCopilot
}) => {
  const [data, setData] = useState<DivergenceRadarResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'all' | 'zone_1' | 'zone_2' | 'zone_3' | 'zone_4'>('all');
  const [error, setError] = useState<string | null>(null);

  const loadRadarData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDivergenceRadar();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load divergence radar data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadRadarData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const zone1Items = data?.quadrants.zone_1_accumulation.items || [];
  const zone2Items = data?.quadrants.zone_2_distribution.items || [];
  const zone3Items = data?.quadrants.zone_3_momentum.items || [];
  const zone4Items = data?.quadrants.zone_4_capitulation.items || [];

  const getFilteredItems = (): DivergenceAnomaly[] => {
    if (!data) return [];
    switch (activeTab) {
      case 'zone_1':
        return zone1Items;
      case 'zone_2':
        return zone2Items;
      case 'zone_3':
        return zone3Items;
      case 'zone_4':
        return zone4Items;
      default:
        return [
          ...zone1Items,
          ...zone2Items,
          ...zone3Items,
          ...zone4Items
        ].sort((a, b) => b.abs_divergence - a.abs_divergence);
    }
  };

  const filteredItems = getFilteredItems();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div 
        className="relative w-full max-w-6xl max-h-[92vh] flex flex-col rounded-2xl border border-surface-border bg-[#0B0E14] text-slate-100 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-surface-border px-6 py-4 bg-gradient-to-r from-surface via-[#131924] to-surface">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30 text-indigo-400">
              <Radar className="h-6 w-6 animate-spin-slow" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight text-white">
                  Smart Divergence & Mispricing Radar
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                  <Sparkles className="h-3 w-3" /> NSE / BSE Matrix
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Institutional anomaly detector flagging decouplings between verified news catalysts and realized price returns
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadRadarData}
              disabled={loading}
              className="p-2 rounded-lg border border-surface-border bg-surface hover:bg-surface-hover text-slate-400 hover:text-white transition"
              title="Refresh Radar Scan"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg border border-surface-border bg-surface hover:bg-surface-hover text-slate-400 hover:text-white transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Metric Summary Ribbon */}
        {data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 border-b border-surface-border bg-[#0E121A]">
            {/* Disconnect Index */}
            <div className="p-3 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Market Disconnect Index</span>
                <div className="flex items-baseline gap-1.5 mt-0.5">
                  <span className="text-xl font-mono font-bold text-indigo-400">
                    {data.market_disconnect_index}
                  </span>
                  <span className="text-[10px] text-indigo-300/70 font-mono">pts intensity</span>
                </div>
              </div>
              <Compass className="h-6 w-6 text-indigo-400/40" />
            </div>

            {/* Zone 1: Dip-Buy Opportunities */}
            <div 
              onClick={() => setActiveTab('zone_1')}
              className={`p-3 rounded-xl border cursor-pointer transition ${
                activeTab === 'zone_1' 
                  ? 'border-emerald-500 bg-emerald-500/15 shadow-lg shadow-emerald-500/10' 
                  : 'border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Zone 1: Dip-Buy Opportunities</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">
                  Accumulate
                </span>
              </div>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-xl font-mono font-bold text-emerald-400">
                  {zone1Items.length}
                </span>
                <span className="text-[10px] text-slate-400">stocks lagging catalyst</span>
              </div>
            </div>

            {/* Zone 2: Bull Trap Warnings */}
            <div 
              onClick={() => setActiveTab('zone_2')}
              className={`p-3 rounded-xl border cursor-pointer transition ${
                activeTab === 'zone_2' 
                  ? 'border-rose-500 bg-rose-500/15 shadow-lg shadow-rose-500/10' 
                  : 'border-rose-500/20 bg-rose-500/5 hover:bg-rose-500/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">Zone 2: Retail Bull Traps</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300">
                  Distribution
                </span>
              </div>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-xl font-mono font-bold text-rose-400">
                  {zone2Items.length}
                </span>
                <span className="text-[10px] text-slate-400">false green pumps</span>
              </div>
            </div>

            {/* Total Anomalies */}
            <div 
              onClick={() => setActiveTab('all')}
              className={`p-3 rounded-xl border cursor-pointer transition ${
                activeTab === 'all' 
                  ? 'border-cyan-500 bg-cyan-500/15 shadow-lg shadow-cyan-500/10' 
                  : 'border-cyan-500/20 bg-cyan-500/5 hover:bg-cyan-500/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">Active High-Alpha Signals</span>
                <Zap className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-xl font-mono font-bold text-cyan-300">
                  {data.total_anomalies}
                </span>
                <span className="text-[10px] text-slate-400">monitored equities</span>
              </div>
            </div>
          </div>
        )}

        {/* Quadrant Tabs Navigation */}
        <div className="flex items-center gap-2 px-6 pt-3 pb-1 border-b border-surface-border overflow-x-auto text-xs bg-[#0B0E14]">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              activeTab === 'all'
                ? 'bg-slate-700 text-white font-bold'
                : 'text-slate-400 hover:text-white hover:bg-surface'
            }`}
          >
            All Signals ({data?.total_anomalies || 0})
          </button>

          <button
            onClick={() => setActiveTab('zone_1')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
              activeTab === 'zone_1'
                ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-bold'
                : 'text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/5'
            }`}
          >
            <TrendingDown className="h-3.5 w-3.5 text-emerald-400" />
            Zone 1: Accumulation / Dip-Buy ({zone1Items.length})
          </button>

          <button
            onClick={() => setActiveTab('zone_2')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
              activeTab === 'zone_2'
                ? 'bg-rose-500/20 border border-rose-500/40 text-rose-300 font-bold'
                : 'text-slate-400 hover:text-rose-400 hover:bg-rose-500/5'
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
            Zone 2: Distribution Bull Trap ({zone2Items.length})
          </button>

          <button
            onClick={() => setActiveTab('zone_3')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
              activeTab === 'zone_3'
                ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 font-bold'
                : 'text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/5'
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5 text-cyan-400" />
            Zone 3: Momentum Breakout ({zone3Items.length})
          </button>

          <button
            onClick={() => setActiveTab('zone_4')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
              activeTab === 'zone_4'
                ? 'bg-purple-500/20 border border-purple-500/40 text-purple-300 font-bold'
                : 'text-slate-400 hover:text-purple-400 hover:bg-purple-500/5'
            }`}
          >
            <ShieldAlert className="h-3.5 w-3.5 text-purple-400" />
            Zone 4: Capitulation Breakdown ({zone4Items.length})
          </button>
        </div>

        {/* Modal Body / Cards Grid */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
              <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
              <p className="text-sm">Calculating price-sentiment divergence cross-matrices...</p>
            </div>
          ) : error ? (
            <div className="py-12 text-center text-rose-400 bg-rose-500/5 border border-rose-500/20 rounded-xl p-4">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-rose-400" />
              <p className="font-semibold">Unable to run divergence radar</p>
              <p className="text-xs text-rose-300/80 mt-1">{error}</p>
              <button
                onClick={loadRadarData}
                className="mt-4 px-4 py-1.5 text-xs font-semibold rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 transition"
              >
                Try Again
              </button>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Compass className="h-10 w-10 mx-auto mb-2 text-slate-500/50" />
              <p className="text-sm font-semibold">No active mispricing anomalies in this quadrant</p>
              <p className="text-xs text-slate-500 mt-1">
                Prices and sentiment in this segment are currently tracking in equilibrium.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredItems.map((item) => {
                const isZone1 = item.quadrant_id === 'ZONE_1_ACCUMULATION';
                const isZone2 = item.quadrant_id === 'ZONE_2_DISTRIBUTION';
                const isZone3 = item.quadrant_id === 'ZONE_3_MOMENTUM';
                const isZone4 = item.quadrant_id === 'ZONE_4_CAPITULATION';

                const cardBorder = isZone1 
                  ? 'border-emerald-500/30 hover:border-emerald-500/60 bg-gradient-to-b from-emerald-500/5 via-surface to-surface'
                  : isZone2 
                  ? 'border-rose-500/30 hover:border-rose-500/60 bg-gradient-to-b from-rose-500/5 via-surface to-surface'
                  : isZone3
                  ? 'border-cyan-500/30 hover:border-cyan-500/60 bg-gradient-to-b from-cyan-500/5 via-surface to-surface'
                  : 'border-purple-500/30 hover:border-purple-500/60 bg-gradient-to-b from-purple-500/5 via-surface to-surface';

                const badgeBg = isZone1
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : isZone2
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : isZone3
                  ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                  : 'bg-purple-500/10 text-purple-400 border-purple-500/30';

                return (
                  <div 
                    key={item.symbol}
                    className={`rounded-xl border p-4 transition-all duration-200 shadow-md flex flex-col justify-between ${cardBorder}`}
                  >
                    <div>
                      {/* Top Row: Symbol, Sector, Quadrant Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-mono text-lg font-bold text-white tracking-wide">
                              {item.symbol}
                            </h3>
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-border text-slate-300">
                              {item.sector}
                            </span>
                            {item.is_single_stock && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                Single-Stock Catalyst
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="font-mono text-sm font-semibold text-slate-200">
                              ₹{item.price.toFixed(2)}
                            </span>
                            <span className={`flex items-center text-xs font-mono font-bold ${
                              item.percent_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {item.percent_change >= 0 ? (
                                <ArrowUpRight className="h-3.5 w-3.5 inline mr-0.5" />
                              ) : (
                                <ArrowDownRight className="h-3.5 w-3.5 inline mr-0.5" />
                              )}
                              {item.percent_change > 0 ? `+${item.percent_change}%` : `${item.percent_change}%`}
                            </span>
                          </div>
                        </div>

                        {/* Quadrant Indicator */}
                        <div className="text-right">
                          <span className={`inline-block px-2.5 py-1 rounded-md text-[10px] font-bold border ${badgeBg}`}>
                            {item.quadrant_label}
                          </span>
                          <span className="block text-[9px] font-mono text-slate-400 mt-1">
                            Conviction: <strong className="text-slate-200">{item.conviction}</strong>
                          </span>
                        </div>
                      </div>

                      {/* Divergence Disconnect Bar */}
                      <div className="mt-3.5 p-2.5 rounded-lg bg-[#0B0E14]/80 border border-surface-border">
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] uppercase font-bold text-slate-400">Sentiment Score:</span>
                            <span className={`font-mono font-bold ${
                              item.sentiment_score > 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {item.sentiment_score > 0 ? `+${item.sentiment_score}` : item.sentiment_score} ({item.sentiment_label})
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-[10px] uppercase font-bold text-slate-400">Disconnect:</span>
                            <span className="font-mono font-bold text-indigo-300">
                              {item.divergence_score > 0 ? `+${item.divergence_score}` : item.divergence_score}
                            </span>
                          </div>
                        </div>

                        {/* Visual Target & Stop Playbook */}
                        <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] font-mono">
                          <div className="flex items-center gap-1 text-emerald-400">
                            <span className="text-slate-400 text-[10px]">Rebound / Target:</span>
                            <strong>{item.rebound_target_pct > 0 ? `+${item.rebound_target_pct}%` : `${item.rebound_target_pct}%`}</strong>
                          </div>
                          <div className="flex items-center gap-1 text-slate-400">
                            <span className="text-[10px]">Hedge Stop:</span>
                            <strong className="text-rose-400">-{item.trailing_stop_pct}%</strong>
                          </div>
                        </div>
                      </div>

                      {/* Action Description */}
                      <div className="mt-2 text-xs text-slate-300 bg-surface/50 p-2 rounded-md border border-surface-border flex items-start gap-1.5">
                        <span className="font-bold text-[10px] px-1.5 py-0.5 rounded bg-surface-border text-white">
                          {item.action_code}
                        </span>
                        <p className="text-[11px] text-slate-300 leading-relaxed">
                          {item.action_description}
                        </p>
                      </div>

                      {/* Verified Catalyst Link */}
                      <div className="mt-2.5">
                        <span className="text-[9px] uppercase font-bold text-slate-400 block mb-0.5">
                          Verified Catalyst:
                        </span>
                        <a
                          href={item.catalyst_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-300 hover:text-indigo-200 line-clamp-1 underline decoration-indigo-500/40 hover:decoration-indigo-300 flex items-center gap-1"
                        >
                          {item.catalyst_headline}
                          <ExternalLink className="h-3 w-3 shrink-0 inline text-slate-400" />
                        </a>
                      </div>
                    </div>

                    {/* Card Actions Bottom */}
                    <div className="mt-3 pt-2.5 border-t border-surface-border/60 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-slate-400">
                        {item.catalyst_type}
                      </span>
                      {onOpenCopilot && (
                        <button
                          onClick={() => {
                            onClose();
                            onOpenCopilot(item.symbol);
                          }}
                          className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
                        >
                          Ask Copilot about {item.symbol} &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-surface-border bg-[#0E121A] flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Radar dynamically recalculates on incoming NSE corporate filings & trade ticks</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg border border-surface-border bg-surface hover:bg-surface-hover text-slate-200 text-xs font-semibold transition"
          >
            Close Radar
          </button>
        </div>
      </div>
    </div>
  );
};
