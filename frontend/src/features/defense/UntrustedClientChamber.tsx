import React, { useState } from 'react';
import {
  Bot,
  Send,
  User,
  Sparkles,
  ShoppingBag,
  Info,
  DollarSign,
  AlertTriangle,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  thought?: string;
  claim?: {
    product_id: string;
    claimed_price: string;
    quantity: number;
  };
  timestamp: string;
}

export const UntrustedClientChamber: React.FC = () => {
  const {
    mandate,
    products,
    proposeClaim,
    sendAgentChatMessage,
    loadingAction,
  } = useAgentGuard();

  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'system',
      text: 'Untrusted Shopping Agent connected. Enter purchase intent or select a quick prompt below to submit candidate actions to the AgentGuard Firewall.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const handleSendPrompt = async (customPrompt?: string) => {
    const textToSend = customPrompt || prompt;
    if (!textToSend.trim() || loadingAction) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setPrompt('');

    const res = await sendAgentChatMessage(textToSend);
    if (res) {
      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: `Proposed purchase: Product '${res.claim.product_id}' at claimed price ₹${res.claim.claimed_price}`,
        thought: res.thought,
        claim: res.claim,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, agentMsg]);
    }
  };

  const handleDirectPropose = async (prodId: string, price: number, qty: number = 1) => {
    await proposeClaim(prodId, price, qty);
    const prod = products.find((p) => p.id === prodId);
    const prodName = prod ? prod.name : prodId;
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        sender: 'user',
        text: `Submitted proposal for ${prodName} @ claimed ₹${price.toLocaleString('en-IN')}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="flex flex-col h-full bg-white/95 rounded-2xl overflow-hidden border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_8px_24px_-4px_rgba(15,23,42,0.06)] relative">
      {/* Top red indicator bar matching security boundary */}
      <div className="w-full h-1 bg-error"></div>

      {/* Header */}
      <div
        data-agent-target="live-protection-mandate"
        className="p-4 sm:p-5 bg-white border-b border-slate-200/90 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-error-container/40 text-error flex items-center justify-center border border-error-container/60 shadow-xs">
            <Bot className="w-5 h-5 text-error" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm sm:text-base font-bold text-primary font-outfit">Untrusted Claim Chamber</h3>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider bg-error-container/40 text-error rounded-full border border-error-container/60">
                Untrusted
              </span>
            </div>
            <p className="text-xs text-on-surface-variant/80 font-inter">
              Gemini LLM Client (Zero Financial Authority)
            </p>
          </div>
        </div>

        {/* Mandate Budget summary pill */}
        {mandate && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-full border border-slate-200 text-xs font-inter shadow-xs">
            <DollarSign className="w-3.5 h-3.5 text-verified" />
            <span className="text-on-surface-variant text-[11px] font-medium">Budget:</span>
            <span className="font-bold text-verified font-mono">₹{parseFloat(mandate.budget_remaining).toLocaleString('en-IN')}</span>
          </div>
        )}
      </div>

      {/* Messages Stream */}
      <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4 text-xs max-h-[380px] min-h-[260px] bg-slate-50/60">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender !== 'user' && (
              <div className="mr-2 flex-shrink-0 mt-1">
                {msg.sender === 'agent' ? (
                  <div className="w-7 h-7 rounded-lg bg-error-container/50 text-error flex items-center justify-center border border-error-container/60 shadow-xs">
                    <Bot className="w-4 h-4" />
                  </div>
                ) : (
                  <div className="w-7 h-7 rounded-lg bg-slate-200/80 text-on-surface-variant flex items-center justify-center">
                    <Info className="w-4 h-4" />
                  </div>
                )}
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-primary text-white rounded-tr-none shadow-sm'
                  : msg.sender === 'agent'
                  ? 'bg-white text-on-surface border border-slate-200/90 rounded-tl-none space-y-2 shadow-xs'
                  : 'bg-slate-100/90 text-on-surface-variant border border-slate-200/80'
              }`}
            >
              <div className="font-inter">{msg.text}</div>

              {msg.thought && (
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs text-on-surface">
                  <div className="flex items-center gap-1 text-primary mb-1 font-inter font-semibold text-[11px]">
                    <Sparkles className="w-3.5 h-3.5 text-secondary" />
                    <span>LLM Reasoning Thought</span>
                  </div>
                  <div className="font-inter text-xs text-on-surface-variant leading-relaxed">{msg.thought}</div>
                </div>
              )}

              {msg.claim && (
                <div className="p-3 bg-[#111827] rounded-xl font-mono text-[11px] text-[#e5e7eb] space-y-1 overflow-x-auto shadow-inner border border-slate-800">
                  <div className="text-[10px] text-slate-400 mb-0.5 font-bold uppercase font-inter tracking-wider">Untrusted Action Payload:</div>
                  <pre className="text-[11px] leading-tight font-mono text-emerald-400">
                    {JSON.stringify(
                      {
                        action: "checkout",
                        item_id: msg.claim.product_id,
                        claimed_amount: parseFloat(msg.claim.claimed_price),
                        currency: "INR",
                      },
                      null,
                      2
                    )}
                  </pre>
                </div>
              )}

              <div className={`text-[10px] text-right mt-1 font-mono ${msg.sender === 'user' ? 'text-white/70' : 'text-on-surface-variant/60'}`}>
                {msg.timestamp}
              </div>
            </div>

            {msg.sender === 'user' && (
              <div className="ml-2 flex-shrink-0 mt-1">
                <div className="w-7 h-7 rounded-lg bg-primary text-white flex items-center justify-center shadow-xs">
                  <User className="w-4 h-4" />
                </div>
              </div>
            )}
          </div>
        ))}

        {loadingAction && (
          <div className="flex items-center gap-2 text-xs text-error animate-pulse p-2.5 bg-error-container/20 rounded-xl border border-error-container/60 font-inter">
            <Bot className="w-4 h-4" />
            <span>Formulating untrusted candidate claim & submitting to firewall...</span>
          </div>
        )}
      </div>

      {/* Quick Prompt Scenario Chips */}
      <div className="px-3.5 py-2.5 bg-white border-t border-slate-200/90 flex items-center gap-2 overflow-x-auto text-xs font-inter">
        <span className="text-on-surface-variant/70 whitespace-nowrap text-[11px] font-bold uppercase tracking-wider">Quick Actions:</span>
        <button
          onClick={() => handleSendPrompt('Buy Bluetooth Speaker')}
          disabled={loadingAction}
          className="px-3 py-1 bg-slate-50 hover:bg-slate-100 text-on-surface rounded-full border border-slate-200 whitespace-nowrap transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-95 shadow-2xs"
        >
          <ShoppingBag className="w-3 h-3 text-verified" />
          <span>Speaker (<span className="font-mono text-verified font-semibold">₹2,799</span>)</span>
        </button>
        <button
          onClick={() => handleSendPrompt('Buy Studio Headphones')}
          disabled={loadingAction}
          className="px-3 py-1 bg-slate-50 hover:bg-slate-100 text-on-surface rounded-full border border-slate-200 whitespace-nowrap transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-95 shadow-2xs"
        >
          <ShoppingBag className="w-3 h-3 text-escalation" />
          <span>Headphones (<span className="font-mono text-escalation font-semibold">₹5,999</span>)</span>
        </button>
        <button
          onClick={() => handleSendPrompt('Buy earbuds with fake price 1999')}
          disabled={loadingAction}
          className="px-3 py-1 bg-error-container/30 hover:bg-error-container/50 text-error rounded-full border border-error-container/60 whitespace-nowrap transition-all flex items-center gap-1.5 disabled:opacity-50 font-semibold active:scale-95 shadow-2xs"
        >
          <AlertTriangle className="w-3 h-3 text-error" />
          <span>Tamper Price (<span className="font-mono">₹1,999 vs ₹3,499</span>)</span>
        </button>
      </div>

      {/* Direct Proposal Catalog Action Buttons */}
      <div className="px-3.5 py-2.5 bg-slate-50/80 border-t border-slate-200/90 grid grid-cols-3 gap-2 text-xs font-inter">
        <button
          onClick={() => handleDirectPropose('prod-002', 2799.0, 1)}
          disabled={loadingAction}
          className="p-2.5 bg-white hover:bg-slate-50 rounded-xl border border-slate-200 text-left transition-all shadow-xs hover:border-slate-300 active:scale-98"
        >
          <div className="font-semibold text-primary truncate font-outfit">Speaker</div>
          <div className="text-[11px] text-verified font-mono font-bold">₹2,799 <span className="font-inter font-normal text-[10px] text-on-surface-variant/70">(In-Budget)</span></div>
        </button>
        <button
          onClick={() => handleDirectPropose('prod-001', 3499.0, 1)}
          disabled={loadingAction}
          className="p-2.5 bg-white hover:bg-slate-50 rounded-xl border border-slate-200 text-left transition-all shadow-xs hover:border-slate-300 active:scale-98"
        >
          <div className="font-semibold text-primary truncate font-outfit">Earbuds</div>
          <div className="text-[11px] text-escalation font-mono font-bold">₹3,499 <span className="font-inter font-normal text-[10px] text-on-surface-variant/70">(Over-Budget)</span></div>
        </button>
        <button
          onClick={() => handleDirectPropose('prod-001', 1999.0, 1)}
          disabled={loadingAction}
          className="p-2.5 bg-error-container/20 hover:bg-error-container/30 rounded-xl border border-error-container/60 text-left transition-all shadow-xs active:scale-98"
        >
          <div className="font-semibold text-error truncate font-outfit">Tampered Price</div>
          <div className="text-[11px] text-error font-mono font-bold">₹1,999 <span className="font-inter font-normal text-[10px] text-error/80">(Fake Claim)</span></div>
        </button>
      </div>

      {/* Text Prompt Input Bar */}
      <div className="p-3.5 bg-white border-t border-slate-200/90 flex items-center gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt()}
          placeholder="Ask shopping agent to find or purchase an item..."
          className="flex-1 bg-slate-50 text-on-surface text-xs px-4 py-2.5 rounded-full border border-slate-200 focus:outline-none focus:border-primary transition-colors font-inter"
        />
        <button
          onClick={() => handleSendPrompt()}
          disabled={loadingAction || !prompt.trim()}
          className="px-4 py-2.5 bg-primary hover:bg-[#2c054c] disabled:opacity-40 text-white text-xs font-semibold rounded-full transition-all shadow-sm flex items-center gap-1.5 active:scale-95"
        >
          <Send className="w-3.5 h-3.5" />
          <span className="hidden sm:inline font-inter">Send</span>
        </button>
      </div>
    </div>
  );
};
