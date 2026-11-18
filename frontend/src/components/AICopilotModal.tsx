import React, { useState } from 'react';
import { Bot, Send, X, Sparkles, ExternalLink, ShieldCheck, HelpCircle } from 'lucide-react';
import { queryCopilot } from '../api';
import { CopilotResponse } from '../types';

interface AICopilotProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AICopilotModal: React.FC<AICopilotProps> = ({ isOpen, onClose }) => {
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState<Array<{
    query: string;
    response?: CopilotResponse;
    error?: string;
  }>>([
    {
      query: 'Initial Prompt',
      response: {
        answer: 'Hello! I am your FinSentiq Market Copilot. Ask me about any Indian stock, sector momentum, or breaking catalyst.',
        relevant_symbols: ['RELIANCE', 'HDFCBANK', 'TCS'],
        referenced_articles: [],
        confidence: 1.0,
      },
    },
  ]);

  if (!isOpen) return null;

  const handleSend = async (text?: string) => {
    const q = (text || inputQuery).trim();
    if (!q || loading) return;

    setInputQuery('');
    setLoading(true);

    const newIndex = conversation.length;
    setConversation((prev) => [...prev, { query: q }]);

    try {
      const res = await queryCopilot(q);
      setConversation((prev) => {
        const copy = [...prev];
        copy[newIndex] = { query: q, response: res };
        return copy;
      });
    } catch (err: any) {
      setConversation((prev) => {
        const copy = [...prev];
        copy[newIndex] = {
          query: q,
          error: 'Could not connect to Copilot engine. Please try again.',
        };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    'Why is Banking sector active today?',
    'Top positive catalysts across NSE',
    'Summarize Auto sector momentum',
    'What is moving IT stocks?',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-2xl border border-surface-border bg-surface shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-[#0B0E14]/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                FinSentiq AI Market Copilot
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Llama 3.3 Active
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Institutional synthesis of real-time Indian news &amp; sectoral signals
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

        {/* Conversation Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {conversation.map((msg, idx) => (
            <div key={idx} className="space-y-2">
              {idx > 0 && (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-xl bg-indigo-600 text-white px-3.5 py-2 text-xs font-medium shadow">
                    {msg.query}
                  </div>
                </div>
              )}

              {msg.response && (
                <div className="flex justify-start">
                  <div className="max-w-[95%] rounded-xl bg-[#0B0E14]/80 border border-surface-border p-3.5 text-xs text-slate-200 space-y-2.5">
                    <div className="flex items-center gap-2 text-indigo-400 font-semibold text-[11px]">
                      <Sparkles className="h-3.5 w-3.5" />
                      FinSentiq Analyst Insight
                    </div>
                    <p className="leading-relaxed">{msg.response.answer}</p>

                    {/* Stock mentions */}
                    {msg.response.relevant_symbols.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        <span className="text-[10px] text-slate-400">Related Tickers:</span>
                        {msg.response.relevant_symbols.map((sym) => (
                          <span
                            key={sym}
                            className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-bold"
                          >
                            {sym}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Citations */}
                    {msg.response.referenced_articles && msg.response.referenced_articles.length > 0 && (
                      <div className="border-t border-slate-800 pt-2 space-y-1">
                        <span className="text-[10px] font-bold text-slate-400 block uppercase tracking-wider">
                          Referenced Intelligence:
                        </span>
                        {msg.response.referenced_articles.map((art, aIdx) => (
                          <a
                            key={aIdx}
                            href={art.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between text-[11px] text-slate-300 hover:text-indigo-400 transition"
                          >
                            <span className="truncate max-w-[85%]">• {art.title}</span>
                            <ExternalLink className="h-3 w-3 shrink-0 ml-1 text-slate-400" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {msg.error && (
                <div className="text-xs text-rose-400 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
                  {msg.error}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-slate-400 italic py-2">
              <div className="h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
              Synthesizing real-time news feeds &amp; sector sentiment...
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div className="px-4 py-2 border-t border-surface-border bg-[#0B0E14]/40 flex items-center gap-2 overflow-x-auto text-[11px]">
          <span className="text-slate-400 shrink-0 flex items-center gap-1">
            <HelpCircle className="h-3 w-3" /> Quick:
          </span>
          {samplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              className="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-indigo-600/30 hover:border-indigo-500/40 text-slate-300 text-[10px] border border-slate-700 transition"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-surface-border bg-[#0B0E14]/80 flex items-center gap-2">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about any stock, sector trend, or catalyst..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !inputQuery.trim()}
            className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

      </div>
    </div>
  );
};
