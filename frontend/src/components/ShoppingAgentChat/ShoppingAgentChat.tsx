import React, { useState } from 'react';
import { Send, Bot, User, ShieldAlert, Sparkles, ShoppingBag, DollarSign } from 'lucide-react';
import { Mandate, api, AgentChatResponseData } from '../../lib/api';


interface Message {
  id: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  thought?: string;
  claim?: {
    product_id: string;
    claimed_price: string;
    quantity: number;
  };
  firewall_result?: any;
  timestamp: string;
}

interface ShoppingAgentChatProps {
  mandate: Mandate | null;
  onNewTransaction: (txnResult: any, agentClaim?: any) => void;
  onRefreshMandate: () => void;
}

export const ShoppingAgentChat: React.FC<ShoppingAgentChatProps> = ({
  mandate,
  onNewTransaction,
  onRefreshMandate,
}) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'system',
      text: 'Reference Shopping Agent ready. Enter a purchase request or choose a quick prompt to test the Agentic Commerce Firewall.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const handleSend = async (customPrompt?: string) => {
    const textToSend = customPrompt || prompt;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setPrompt('');
    setLoading(true);

    try {
      const { envelope } = await api.agentChat(textToSend);
      if (envelope.success && envelope.data) {
        const data: AgentChatResponseData = envelope.data;

        const agentMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'agent',
          text: `Proposed purchase for Product ID '${data.agent_claim.product_id}' at claimed price ₹${data.agent_claim.claimed_price}`,
          thought: data.agent_thought,
          claim: data.agent_claim,
          firewall_result: data.firewall_result,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setMessages((prev) => [...prev, agentMsg]);

        if (data.firewall_result) {
          onNewTransaction(data.firewall_result, data.agent_claim);
        }
      } else {
        const errorMsg: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'system',
          text: `Error: ${envelope.error?.message || 'Failed to communicate with shopping agent'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      onRefreshMandate();
    }
  };

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
      {/* Header */}
      <div className="p-4 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-semibold text-slate-100">Shopping Agent</h2>
              <span className="px-2 py-0.5 text-[10px] font-mono font-medium bg-amber-500/10 text-amber-400 rounded border border-amber-500/20">
                UNTRUSTED CLIENT
              </span>
            </div>
            <p className="text-xs text-slate-400">Gemini LLM Assistant (Zero Authorization Power)</p>
          </div>
        </div>

        {/* Mandate Summary Badge */}
        {mandate && (
          <div className="flex items-center space-x-3 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
            <div className="flex items-center space-x-1.5 text-slate-300">
              <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
              <span>Budget:</span>
              <span className="font-mono text-emerald-400 font-medium">₹{parseFloat(mandate.budget_remaining).toLocaleString('en-IN')}</span>
              <span className="text-slate-500">/ ₹{parseFloat(mandate.budget_total).toLocaleString('en-IN')}</span>
            </div>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase ${
                mandate.status === 'active'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              {mandate.status}
            </span>
          </div>
        )}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.sender === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.sender !== 'user' && (
              <div className="mr-2 flex-shrink-0 mt-1">
                {msg.sender === 'agent' ? (
                  <div className="p-1.5 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
                    <Bot className="w-4 h-4" />
                  </div>
                ) : (
                  <div className="p-1.5 bg-slate-800 text-slate-400 rounded-lg">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                )}
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-xl p-3 text-xs leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none'
                  : msg.sender === 'agent'
                  ? 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-tl-none space-y-2'
                  : 'bg-slate-950 text-slate-400 border border-slate-800/80'
              }`}
            >
              <div>{msg.text}</div>

              {msg.thought && (
                <div className="p-2 bg-slate-950/80 rounded border border-slate-800/60 font-mono text-[11px] text-slate-400">
                  <div className="flex items-center space-x-1 text-indigo-400 mb-1 font-sans font-medium text-[10px]">
                    <Sparkles className="w-3 h-3" />
                    <span>AGENT REASONING</span>
                  </div>
                  {msg.thought}
                </div>
              )}

              {msg.claim && (
                <div className="p-2 bg-indigo-950/30 rounded border border-indigo-500/20 text-[11px] font-mono text-indigo-200 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Claimed Price:</span>
                    <span className="font-semibold text-indigo-300">₹{msg.claim.claimed_price}</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-400">Product ID:</span>
                    <span className="text-slate-300">{msg.claim.product_id}</span>
                  </div>
                </div>
              )}

              <div className="text-[10px] text-slate-500 text-right mt-1 font-mono">
                {msg.timestamp}
              </div>
            </div>

            {msg.sender === 'user' && (
              <div className="ml-2 flex-shrink-0 mt-1">
                <div className="p-1.5 bg-indigo-600/30 text-indigo-300 rounded-lg">
                  <User className="w-4 h-4" />
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-indigo-400 animate-pulse p-2">
            <Bot className="w-4 h-4" />
            <span>Agent is interpreting catalog and formulating transaction claim...</span>
          </div>
        )}
      </div>

      {/* Quick Action Prompt Chips */}
      <div className="px-4 py-2 bg-slate-900/60 border-t border-slate-800/60 flex items-center space-x-2 overflow-x-auto text-[11px]">
        <span className="text-slate-500 whitespace-nowrap font-mono text-[10px]">QUICK PROMPTS:</span>
        <button
          onClick={() => handleSend('Buy Bluetooth Speaker')}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700/60 whitespace-nowrap transition-colors flex items-center space-x-1"
        >
          <ShoppingBag className="w-3 h-3 text-emerald-400" />
          <span>Speaker (₹2,799)</span>
        </button>
        <button
          onClick={() => handleSend('Buy Studio Headphones')}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700/60 whitespace-nowrap transition-colors flex items-center space-x-1"
        >
          <ShoppingBag className="w-3 h-3 text-amber-400" />
          <span>Headphones (₹5,999)</span>
        </button>
        <button
          onClick={() => handleSend('Buy earbuds with fake price 1999')}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700/60 whitespace-nowrap transition-colors flex items-center space-x-1"
        >
          <ShieldAlert className="w-3 h-3 text-rose-400" />
          <span>Tamper Earbuds (₹1,999 vs ₹3,499)</span>
        </button>
      </div>

      {/* Input Form */}
      <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask shopping agent to buy an item..."
          className="flex-1 bg-slate-950 text-slate-200 text-xs px-3 py-2.5 rounded-lg border border-slate-800 focus:outline-none focus:border-indigo-500/50 transition-colors font-sans"
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !prompt.trim()}
          className="px-3 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors flex items-center space-x-1"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
