import React, { useState } from 'react';
import {
  Mic,
  X,
  Bot,
  User,
  Zap,
  Send,
  Play,
  History,
  Cpu,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const ConversationalVoiceDrawer: React.FC = () => {
  const {
    isConversationalOpen,
    setIsConversationalOpen,
    agentVoiceState,
    setAgentVoiceState,
    triggerScenario,
    setActiveSurfaceTab,
    sendAgentChatMessage,
    loadingAction,
  } = useAgentGuard();

  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<
    { sender: 'user' | 'agent'; text: string; actionTriggered?: string }[]
  >([
    {
      sender: 'agent',
      text: "Hello! I am the AgentGuard Conversational Assistant. I can guide you through the firewall architecture, trigger live threat scenarios, or inspect the cryptographic evidence ledger.",
    },
  ]);

  if (!isConversationalOpen) return null;

  const handleSendQuery = async (queryText: string) => {
    if (!queryText.trim() || loadingAction) return;

    const userText = queryText;
    setChatInput('');
    setMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setAgentVoiceState('THINKING');

    const lower = userText.toLowerCase();

    if (lower.includes('tamper') || lower.includes('price') || lower.includes('fake') || lower.includes('simulation')) {
      setTimeout(async () => {
        setAgentVoiceState('EXECUTING');
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            text: "Triggering Price Tampering Attack scenario (Claimed ₹1,999 vs Catalog ₹3,499). The firewall evaluates the claim against PostgreSQL and issues a DENY verdict.",
            actionTriggered: 'SCENARIO_3_PRICE_TAMPERING',
          },
        ]);
        setActiveSurfaceTab('DEFENSE');
        await triggerScenario(3);
        setAgentVoiceState('DENIED');
      }, 500);
    } else if (lower.includes('replay') || lower.includes('double')) {
      setTimeout(async () => {
        setAgentVoiceState('EXECUTING');
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            text: "Triggering Replay Attack scenario: Submitting a duplicate execution attempt on an already settled transaction. The firewall halts it with HTTP 409 REPLAY_DETECTED.",
            actionTriggered: 'SCENARIO_4_REPLAY_ATTACK',
          },
        ]);
        setActiveSurfaceTab('DEFENSE');
        await triggerScenario(4);
        setAgentVoiceState('DENIED');
      }, 500);
    } else if (lower.includes('over budget') || lower.includes('budget') || lower.includes('escalate')) {
      setTimeout(async () => {
        setAgentVoiceState('EXECUTING');
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            text: "Triggering Over-Budget scenario. The purchase exceeds mandate limits and escalates to human approver for explicit authorization.",
            actionTriggered: 'SCENARIO_2_OVER_BUDGET',
          },
        ]);
        setActiveSurfaceTab('DEFENSE');
        await triggerScenario(2);
        setAgentVoiceState('WAITING_FOR_APPROVAL');
      }, 500);
    } else if (lower.includes('audit') || lower.includes('ledger') || lower.includes('hash')) {
      setTimeout(() => {
        setAgentVoiceState('SPEAKING');
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            text: "Opening the Cryptographic Evidence Ledger. Every state transition is recorded in an immutable forward SHA-256 hash chain.",
            actionTriggered: 'VIEW_FORENSIC_LEDGER',
          },
        ]);
        setActiveSurfaceTab('FORENSICS');
        setTimeout(() => setAgentVoiceState('IDLE'), 1500);
      }, 400);
    } else {
      const res = await sendAgentChatMessage(userText);
      if (res) {
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            text: `Agent formulated proposal for Product '${res.claim.product_id}' @ claimed ₹${res.claim.claimed_price}. Firewall verdict: ${res.result?.decision || 'DENIED'}`,
          },
        ]);
        setActiveSurfaceTab('DEFENSE');
        setAgentVoiceState(res.result?.decision === 'ALLOW' ? 'SUCCESS' : 'DENIED');
      } else {
        setAgentVoiceState('IDLE');
      }
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-white/95 border-l border-surface-container shadow-2xl backdrop-blur-2xl flex flex-col transition-all duration-300">
      {/* Drawer Header */}
      <div className="p-5 bg-surface border-b border-surface-container flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white ring-4 ring-lavender-tint shadow-sm">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-primary font-outfit">The Voice of Trust</h3>
              <span className="text-xs font-inter font-semibold px-2.5 py-0.5 bg-lavender-tint text-[#4C1D95] rounded-full border border-primary-fixed">
                Client Shell
              </span>
            </div>
            <p className="text-xs text-on-surface-variant font-inter">
              AgentGuard Conversational Interface
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsConversationalOpen(false)}
          className="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded-full transition-colors"
          title="Close Drawer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Central Orb / Presence Visualizer matching Stitch */}
      <div className="p-6 bg-gradient-to-b from-surface to-white flex flex-col items-center justify-center border-b border-surface-container relative overflow-hidden">
        <div className="relative w-28 h-28 flex items-center justify-center my-2">
          <div className="absolute inset-0 border-2 border-secondary-fixed rounded-full animate-ping opacity-30"></div>
          <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-white ring-8 ring-lavender-tint shadow-lg">
            <Mic className="w-8 h-8 text-white" />
          </div>
          <div className="absolute -bottom-2 bg-lavender-tint text-[#4C1D95] text-xs font-inter font-semibold px-3 py-0.5 rounded-full border border-primary-fixed shadow-sm">
            {agentVoiceState}
          </div>
        </div>

        <p className="text-xs text-on-surface-variant font-inter text-center max-w-xs mt-2">
          Ask questions about the architecture or trigger live attacks across the trust boundary.
        </p>
      </div>

      {/* Suggested Actions matching Stitch */}
      <div className="p-4 bg-surface border-b border-surface-container space-y-2">
        <div className="flex items-center gap-1.5 text-xs font-inter uppercase tracking-wider text-outline font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
          <span>Suggested Actions</span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs font-inter">
          <button
            onClick={() => handleSendQuery('Run threat simulation on price tampering')}
            className="p-3 bg-white rounded-xl border border-surface-container hover:border-primary transition-all text-left shadow-sm flex items-center gap-2 group"
          >
            <Play className="w-4 h-4 text-secondary group-hover:scale-110 transition-transform" />
            <div>
              <div className="font-bold text-primary font-outfit">Run Simulation</div>
              <div className="text-[11px] text-on-surface-variant">Test attack defenses</div>
            </div>
          </button>

          <button
            onClick={() => handleSendQuery('Show me the cryptographic audit ledger')}
            className="p-3 bg-white rounded-xl border border-surface-container hover:border-primary transition-all text-left shadow-sm flex items-center gap-2 group"
          >
            <History className="w-4 h-4 text-primary group-hover:scale-110 transition-transform" />
            <div>
              <div className="font-bold text-primary font-outfit">Audit Ledger</div>
              <div className="text-[11px] text-on-surface-variant">Review SHA-256 chain</div>
            </div>
          </button>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs bg-[#FAFBFD]">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.sender === 'agent' && (
              <div className="w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center mr-2 flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-primary text-white rounded-tr-none shadow-sm'
                  : 'bg-white text-on-surface border border-surface-container rounded-tl-none space-y-2 shadow-sm font-inter'
              }`}
            >
              <div>{m.text}</div>
              {m.actionTriggered && (
                <div className="text-[11px] font-inter text-secondary bg-surface-container px-2.5 py-1 rounded-md flex items-center gap-1 font-semibold">
                  <Zap className="w-3 h-3 text-secondary" />
                  <span>Action: {m.actionTriggered}</span>
                </div>
              )}
            </div>

            {m.sender === 'user' && (
              <div className="w-7 h-7 rounded-full bg-secondary text-white flex items-center justify-center ml-2 flex-shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* System Feedback Card matching Stitch */}
      <div className="p-3.5 bg-surface border-t border-surface-container text-xs font-inter flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center flex-shrink-0 shadow-sm">
          <Cpu className="w-4 h-4" />
        </div>
        <div className="flex-grow min-w-0">
          <div className="flex justify-between items-center mb-0.5">
            <span className="font-inter text-xs text-primary font-bold tracking-wider uppercase">System Feedback</span>
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-verified"></span>
              <span className="w-1.5 h-1.5 rounded-full bg-verified opacity-50"></span>
            </div>
          </div>
          <p className="text-xs text-on-surface-variant truncate font-inter">
            Firewall state synchronized. Ready to execute instructions.
          </p>
        </div>
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-white border-t border-surface-container flex items-center gap-2">
        <button
          onClick={() => {
            const nextState = agentVoiceState === 'LISTENING' ? 'IDLE' : 'LISTENING';
            setAgentVoiceState(nextState);
            if (nextState === 'LISTENING') {
              setTimeout(() => {
                handleSendQuery('Show me a price tampering attack');
              }, 2000);
            }
          }}
          className={`p-2.5 rounded-full transition-all ${
            agentVoiceState === 'LISTENING'
              ? 'bg-secondary text-white shadow-lg animate-pulse'
              : 'text-secondary hover:bg-secondary-fixed/50'
          }`}
          title="Toggle Mic Input"
        >
          <Mic className="w-4 h-4" />
        </button>

        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendQuery(chatInput)}
          placeholder="Type or speak instructions..."
          className="flex-1 bg-surface-container-low text-on-surface text-xs px-4 py-2.5 rounded-full border border-surface-container focus:outline-none focus:border-secondary transition-colors font-inter"
        />

        <button
          onClick={() => handleSendQuery(chatInput)}
          disabled={loadingAction || !chatInput.trim()}
          className="p-2.5 bg-primary hover:bg-secondary disabled:opacity-50 text-white rounded-full transition-all shadow-sm flex items-center justify-center"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
