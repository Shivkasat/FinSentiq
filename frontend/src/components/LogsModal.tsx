import React from 'react';
import { X, Terminal, ShieldAlert, CheckCircle2, RotateCw } from 'lucide-react';

interface LogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: string[];
  onRefresh: () => void;
}

export const LogsModal: React.FC<LogsModalProps> = ({ isOpen, onClose, logs, onRefresh }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-2xl border border-surface-border bg-[#0B0E14] p-6 shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-surface-border/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Live Activity & Feed Monitor</h3>
              <p className="text-xs text-slate-400 font-mono">Real-Time Market Data Stream</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onRefresh}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Refresh Logs"
            >
              <RotateCw className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Logs Terminal Window */}
        <div className="mt-4 flex-1 overflow-y-auto p-4 rounded-xl bg-black border border-surface-border font-mono text-xs text-slate-300 space-y-1.5">
          {logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span className="text-emerald-500 select-none">›</span>
              <span className="leading-relaxed">{log}</span>
            </div>
          ))}
          {logs.length === 0 && <p className="text-slate-400">No logs captured yet.</p>}
        </div>

      </div>
    </div>
  );
};
