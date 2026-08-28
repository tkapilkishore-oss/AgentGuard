import React from 'react';
import { Bot, Mic, Sparkles, ArrowRight } from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const ConversationalShellSection: React.FC = () => {
  const { setIsConversationalOpen } = useAgentGuard();

  return (
    <section
      id="conversational-agent"
      className="py-16 sm:py-24 px-4 sm:px-6 max-w-7xl mx-auto w-full"
    >
      <div className="bg-surface rounded-3xl p-8 sm:p-12 border border-surface-container shadow-ambient-2 relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-surface-glow pointer-events-none rounded-full blur-3xl opacity-60" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
          {/* Left Column: Story Description (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-lavender-tint/80 border border-primary-fixed text-[#4C1D95] text-xs font-label-mono font-bold">
              <Sparkles className="w-3.5 h-3.5 text-secondary" />
              <span>THE VOICE OF TRUST</span>
            </div>

            <h2 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary leading-tight">
              Conversational Control Surface
            </h2>

            <p className="font-inter text-sm sm:text-base text-on-surface-variant leading-relaxed">
              Interact with AgentGuard via natural voice and chat commands. Ask architectural questions, trigger adversarial test scenarios, or review cryptographic forensic records in real time.
            </p>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                onClick={() => setIsConversationalOpen(true)}
                className="px-7 py-3.5 bg-primary hover:bg-secondary text-white rounded-full font-inter font-semibold text-sm shadow-md hover:shadow-lg transition-all flex items-center gap-2.5 group"
              >
                <Mic className="w-4 h-4 text-white group-hover:scale-110 transition-transform" />
                <span>Open Conversational Assistant</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Right Column: Visual Shell Preview Card (5 cols) */}
          <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-surface-container shadow-ambient-1 flex flex-col items-center justify-center text-center space-y-4">
            <div className="relative w-24 h-24 flex items-center justify-center my-2">
              <div className="absolute inset-0 bg-lavender-tint rounded-full animate-ping opacity-40"></div>
              <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-white ring-8 ring-lavender-tint shadow-md">
                <Bot className="w-8 h-8 text-white" />
              </div>
            </div>

            <div>
              <h3 className="font-outfit font-bold text-primary text-lg">AgentGuard Assistant</h3>
              <p className="font-inter text-xs text-on-surface-variant mt-1">
                Zero Authorization Client Interface
              </p>
            </div>

            <div className="w-full bg-surface-container-low p-3 rounded-xl border border-surface-container text-xs font-label-mono text-on-surface text-left space-y-1.5">
              <div className="text-[10px] text-outline uppercase font-bold">Suggested Prompt:</div>
              <div className="text-secondary font-bold">"Show me a price tampering attack"</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
