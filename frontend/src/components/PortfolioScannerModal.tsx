import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  X, 
  Plus, 
  Trash2, 
  TrendingUp, 
  TrendingDown, 
  Upload, 
  Sparkles,
  ExternalLink,
  RefreshCw,
  FileSpreadsheet
} from 'lucide-react';
import { scanPortfolio, fetchSamplePortfolioScan } from '../api';
import { PortfolioScanResult, HoldingInput, ScannedHolding } from '../types';

interface PortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
}

export const PortfolioScannerModal: React.FC<PortfolioModalProps> = ({
  isOpen,
  onClose,
  userId = 'guest_user',
}) => {
  const [holdings, setHoldings] = useState<HoldingInput[]>([
    { symbol: 'RELIANCE', quantity: 15, buy_price: 1240 },
    { symbol: 'HDFCBANK', quantity: 25, buy_price: 1720 },
    { symbol: 'TCS', quantity: 10, buy_price: 3850 },
    { symbol: 'TATAMOTORS', quantity: 30, buy_price: 795 },
  ]);

  const [newSymbol, setNewSymbol] = useState('');
  const [newQty, setNewQty] = useState('10');
  const [newPrice, setNewPrice] = useState('');

  const [scanResult, setScanResult] = useState<PortfolioScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleScan = async (itemsToScan = holdings) => {
    if (itemsToScan.length === 0) {
      setError('Please add at least one stock to scan.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await scanPortfolio(itemsToScan, userId);
      setScanResult(res);
    } catch (err: any) {
      setError('Failed to scan portfolio against market feeds.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSamplePortfolioScan();
      setScanResult(res);
      setHoldings(
        res.scanned_holdings.map((h: ScannedHolding) => ({
          symbol: h.symbol,
          quantity: h.quantity,
          buy_price: h.buy_price,
        }))
      );
    } catch (err) {
      setError('Failed to load sample portfolio.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddHolding = () => {
    const sym = newSymbol.trim().toUpperCase();
    const qty = parseInt(newQty) || 10;
    const price = parseFloat(newPrice) || 0.0;

    if (!sym) return;

    const updated = [...holdings.filter((h) => h.symbol !== sym), { symbol: sym, quantity: qty, buy_price: price }];
    setHoldings(updated);
    setNewSymbol('');
    setNewPrice('');
    handleScan(updated);
  };

  const handleRemoveHolding = (sym: string) => {
    const updated = holdings.filter((h) => h.symbol !== sym);
    setHoldings(updated);
    if (updated.length > 0) {
      handleScan(updated);
    } else {
      setScanResult(null);
    }
  };

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;

      const lines = text.split('\n');
      const parsed: HoldingInput[] = [];

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line || i === 0 && line.toLowerCase().includes('symbol')) continue;
        const parts = line.split(',');
        if (parts.length >= 1) {
          const sym = parts[0].trim().toUpperCase().replace('.NS', '').replace('.BO', '');
          const qty = parts.length >= 2 ? parseInt(parts[1].trim()) || 10 : 10;
          const pr = parts.length >= 3 ? parseFloat(parts[2].trim()) || 0 : 0;
          if (sym) {
            parsed.push({ symbol: sym, quantity: qty, buy_price: pr });
          }
        }
      }

      if (parsed.length > 0) {
        setHoldings(parsed);
        handleScan(parsed);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl rounded-2xl border border-surface-border bg-surface shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-[#0B0E14]/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                Portfolio Risk &amp; Catalyst Scanner
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Real-Time Exposure Check
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Cross-references your holdings against 150+ live breaking headlines, RBI updates, and sentiment shocks
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          
          {/* Action Toolbar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-[#0B0E14]/50 border border-surface-border">
            {/* Quick Add Form */}
            <div className="flex items-center gap-2 flex-1">
              <input
                type="text"
                placeholder="Stock (e.g. INFY)"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                className="w-28 sm:w-32 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white uppercase placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
              <input
                type="number"
                placeholder="Qty"
                value={newQty}
                onChange={(e) => setNewQty(e.target.value)}
                className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
              <input
                type="number"
                placeholder="Buy ₹"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="w-20 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
              <button
                onClick={handleAddHolding}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 transition shrink-0"
              >
                <Plus className="h-3.5 w-3.5" /> Add
              </button>
            </div>

            {/* Quick Sample & CSV Upload */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleLoadSample}
                className="px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-800 border border-surface-border text-xs text-slate-300 font-medium flex items-center gap-1.5 transition"
                title="Load sample Indian equity portfolio"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                <span>Load Sample</span>
              </button>

              <label className="cursor-pointer px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-800 border border-surface-border text-xs text-slate-300 font-medium flex items-center gap-1.5 transition">
                <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
                <span>Upload CSV</span>
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleCSVUpload}
                  className="hidden"
                />
              </label>

              <button
                onClick={() => handleScan()}
                disabled={loading}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Run Scanner</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Results Overview Metrics */}
          {scanResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Total Value */}
                <div className="p-3 rounded-xl bg-[#0B0E14]/70 border border-surface-border">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Current Value</span>
                  <p className="font-mono text-base font-bold text-white mt-1">
                    ₹{scanResult.total_current.toLocaleString('en-IN')}
                  </p>
                  <span className="text-[10px] text-slate-400 font-mono">
                    Invested: ₹{scanResult.total_invested.toLocaleString('en-IN')}
                  </span>
                </div>

                {/* Overall PnL */}
                <div className="p-3 rounded-xl bg-[#0B0E14]/70 border border-surface-border">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Unrealized P&amp;L</span>
                  <p className={`font-mono text-base font-bold mt-1 ${scanResult.total_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {scanResult.total_pnl >= 0 ? `+₹${scanResult.total_pnl.toLocaleString('en-IN')}` : `-₹${Math.abs(scanResult.total_pnl).toLocaleString('en-IN')}`}
                  </p>
                  <span className={`text-[10px] font-mono font-bold ${scanResult.total_pnl_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {scanResult.total_pnl_percent >= 0 ? `+${scanResult.total_pnl_percent}%` : `${scanResult.total_pnl_percent}%`}
                  </span>
                </div>

                {/* News Sentiment Score */}
                <div className="p-3 rounded-xl bg-[#0B0E14]/70 border border-surface-border">
                  <span className="text-[10px] uppercase font-bold text-slate-400">News Sentiment Bias</span>
                  <p className={`font-mono text-base font-bold mt-1 ${scanResult.portfolio_sentiment_score > 0 ? 'text-emerald-400' : scanResult.portfolio_sentiment_score < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                    {scanResult.portfolio_sentiment_score > 0 ? `+${scanResult.portfolio_sentiment_score}` : scanResult.portfolio_sentiment_score}
                  </p>
                  <span className="text-[10px] text-slate-400">
                    Weighted across holdings
                  </span>
                </div>

                {/* Risk Rating */}
                <div className="p-3 rounded-xl bg-[#0B0E14]/70 border border-surface-border">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Risk Assessment</span>
                  <p className="text-xs font-bold text-white mt-1 truncate">
                    {scanResult.overall_risk_rating}
                  </p>
                  <span className={`text-[10px] font-bold ${scanResult.flagged_risk_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {scanResult.flagged_risk_count} Alert(s) Active
                  </span>
                </div>
              </div>

              {/* Actionable Summary Alert */}
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-indigo-950/40 via-surface to-indigo-950/40 border border-indigo-500/20 text-xs text-slate-300 flex items-start gap-2.5">
                <ShieldCheck className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block mb-0.5">Automated Intelligence Digest:</strong>
                  <span>{scanResult.actionable_summary}</span>
                </div>
              </div>

              {/* Holdings Risk Table */}
              <div className="rounded-xl border border-surface-border overflow-hidden bg-[#0B0E14]/40">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-surface-border bg-surface text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                      <th className="p-3">Stock / Sector</th>
                      <th className="p-3 text-right">Price / P&amp;L</th>
                      <th className="p-3">News Catalyst &amp; Risk Level</th>
                      <th className="p-3 text-center">Breaking News Impact</th>
                      <th className="p-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border/50 text-slate-300">
                    {scanResult.scanned_holdings.map((h) => (
                      <tr key={h.symbol} className="hover:bg-surface-hover/50 transition">
                        {/* Symbol & Sector */}
                        <td className="p-3">
                          <div className="font-mono font-bold text-white text-xs">{h.symbol}</div>
                          <div className="text-[10px] text-slate-400">{h.sector} • {h.quantity} shares</div>
                        </td>

                        {/* Price & PnL */}
                        <td className="p-3 text-right font-mono">
                          <div className="text-white font-semibold">₹{h.current_price.toLocaleString('en-IN')}</div>
                          <div className={`text-[10px] font-bold ${h.pnl_amount >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {h.pnl_amount >= 0 ? `+${h.pnl_percent}%` : `${h.pnl_percent}%`}
                          </div>
                        </td>

                        {/* Risk & Catalyst */}
                        <td className="p-3">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              h.risk_level.includes('Severe')
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : h.risk_level.includes('Caution')
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                  : h.risk_level.includes('Bullish')
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-slate-800 text-slate-400'
                            }`}>
                              {h.risk_level}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              Score: {h.sentiment_score > 0 ? `+${h.sentiment_score}` : h.sentiment_score}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 line-clamp-1">
                            {h.primary_catalyst} ({h.article_count} news)
                          </span>
                        </td>

                        {/* Headline */}
                        <td className="p-3 max-w-xs">
                          {h.catalyst_link ? (
                            <a
                              href={h.catalyst_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-slate-300 hover:text-indigo-400 line-clamp-2 leading-tight flex items-start gap-1"
                            >
                              <span>{h.catalyst_headline}</span>
                              <ExternalLink className="h-3 w-3 shrink-0 mt-0.5" />
                            </a>
                          ) : (
                            <span className="text-[11px] text-slate-500 italic">
                              {h.catalyst_headline}
                            </span>
                          )}
                        </td>

                        {/* Remove */}
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleRemoveHolding(h.symbol)}
                            className="p-1 rounded text-slate-500 hover:text-rose-400 transition"
                            title="Remove from scanner"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
